import logging
from . import wbuilder_util

# BUILDER
# Takes the parsed bank nodes and rebuilds them to simpler "builder node" (bnode) objects
# with quick access to useful attributes. These bnodes will be later used to generate txtp.
#
# Only used with registered HIRC objects, that have a shortID. Different Wwise parts reuse
# the same HIRC objects, so bnodes are meant to be created once and read-only. 
# Common sub-objects that each HIRC has (like AkRTPCs) are constructed per HIRC using regular
# classes that act like bnodes.

#******************************************************************************

class Builder(object):
    def __init__(self, globalsettings):
        # nodes (default parser nodes) and bnodes (rebuilt simplified nodes)
        self._ref_to_node = {}              # bank + sid + type > parser node
        self._id_to_refs = {}               # sid + type > bank + sid + type list
        self._node_to_bnode = {}            # parser node > rebuilt node

        self._missing_nodes_loaded = {}     # missing nodes that should be in loaded banks (event garbage left by Wwise)
        self._missing_nodes_others = {}     # missing nodes in other banks (even pointing to other banks)
        self._missing_nodes_unknown = {}    # missing nodes of unknown type
        self._missing_nodes_buses = {}      # missing nodes of bus type (usually in init.bnk, but may be in others)
        self._multiple_nodes = {}           # nodes that exist but were loaded in multiple banks and can't decide which one is best

        self._loaded_banks = {}             # id of banks that participate in generating
        self._missing_banks = {}            # banks missing in the "others" list
        self._unknown_props = {}            # object properties that need to be investigated
        self._transition_objects = 0        # info for future support

        # after regular generation we want a list of nodes that weren't used, and
        # generate TXTP for them, but ordered by types since generating some types
        # may end up using other unused types
        self._used_node = {}                # marks which node_refs has been used
        self._hircname_to_nodes = {}        # registered types > list of nodes

        self._globalsettings = globalsettings
        return

    def get_missing_nodes_loaded(self):
        return self._missing_nodes_loaded

    def get_missing_nodes_others(self):
        return self._missing_nodes_others

    def get_missing_nodes_unknown(self):
        return self._missing_nodes_unknown

    def get_missing_nodes_buses(self):
        return self._missing_nodes_buses

    def get_missing_banks(self):
        banks = list(self._missing_banks.keys())
        banks.sort()
        return banks

    def get_multiple_nodes(self):
        return self._multiple_nodes

    def get_transition_objects(self):
        return self._transition_objects

    def get_unknown_props(self):
        return self._unknown_props

    def report_unknown_props(self, unknowns):
        for unknown in unknowns:
            self._unknown_props[unknown] = True

    def report_transition_object(self):
        self._transition_objects += 1

    #--------------------------------------------------------------------------

    # info about loaded banks
    def add_loaded_bank(self, bank_id, bankname):
        self._loaded_banks[bank_id] = bankname

    #--------------------------------------------------------------------------

    # register a new node (should be from HIRC)
    def register_node(self, bank_id, sid, node):
        # Objects can be repeated when saved to different banks, and should be clones (ex. Magatsu Wahrheit, Ori ATWOTW).
        # Except sometimes they aren't, so we need to treat bank+id as separate things (ex. Detroit, Punch Out).
        # Doesn't seem allowed in Wwise but it's possible if devs manually load banks without conflicting ids.
        # ids may be in other banks though, so must also allow finding by single id

        hircname = node.get_name()
        idtype = wbuilder_util.get_builder_hirc_idtype(hircname)

        ref = (bank_id, sid, idtype)

        # add to regular list
        if self._ref_to_node.get(ref) is not None: # common
            logging.debug("generator: ignored repeated node %s + id %s + idtype %s", bank_id, sid, idtype)
            return
        self._ref_to_node[ref] = node

        # in case we don't know the bank on get_node
        subref = (sid, idtype)
        if sid not in self._id_to_refs:
            self._id_to_refs[subref] = []
        self._id_to_refs[subref].append(ref)

        if hircname not in self._hircname_to_nodes:
            self._hircname_to_nodes[hircname] = []
        self._hircname_to_nodes[hircname].append(node)
        return

    # gets a registered node (from HIRC chunk)
    def __get_node(self, bank_id, sid, idtype):
        if idtype is None:
            idtype = wbuilder_util.IDTYPE_AUDIO

        ref = (bank_id, sid, idtype)

        # find node in current bank
        node = self._ref_to_node.get(ref)
        if not node:
            # often objects refer to other objects just by ID, so we don't know the exact bank
            # try to find this id/type in any of the loaded banks
            subref = (sid, idtype)
            refs = self._id_to_refs.get(subref)
            if not refs:
                logging.debug("generator: id %s + idtype %s not found in any bank", sid, idtype)
                return None

            if len(refs) > 1:
                # could try to figure out if nodes are equivalent before reporting? (may happen when loading lots of similar banks)
                logging.debug("generator: id %s + idtype %s found in multiple banks, not found in bank %s", sid, idtype, bank_id)
                self._multiple_nodes[sid] = True
            ref = refs[0]
            node = self._ref_to_node.get(ref)
        return node

    # (transitions pointing or stingers pointing to msegments)
    # for objects that point to other nodes in mswitches/mranseq (that point to segments) don't get used, register to generate at the end
    def _get_node_link(self, ntid):
        if not ntid:
            return None

        tid = ntid.value()
        if not tid:
            return None
        bank_id = ntid.get_root().get_id()

        node = self.__get_node(bank_id, tid, wbuilder_util.IDTYPE_AUDIO)
        #TODO remove? should be used somehow
        __ = self._init_bnode(node) #force parse/register (so doesn't appear as unused), but don't use yet
        return node

    def has_unused(self):
        # find if useful nodes where used
        for hirc_name in wbuilder_util.UNUSED_HIRCS:
            nodes = self._hircname_to_nodes.get(hirc_name, [])
            for node in nodes:
                if id(node) not in self._used_node:
                    name = node.get_name()
                    #remove some false positives
                    if name == 'CAkMusicSegment':
                        #unused segments may not have child nodes (silent segments are ignored)
                        bnode = self._init_bnode(node, mark_used=False)
                        if bnode and bnode.ntids:
                            return True
        return False

    def get_unused_names(self):
        return wbuilder_util.UNUSED_HIRCS

    def get_unused_list(self, hirc_name):
        results = []
        nodes = self._hircname_to_nodes.get(hirc_name, [])
        for node in nodes:
            if id(node) not in self._used_node:
                results.append(node)
        return results

    #--------------------------------------------------------------------------

    def _get_bnode_link_bus(self, ntid):
        return self._get_bnode_link(ntid, idtype=wbuilder_util.IDTYPE_BUS)

    def _get_bnode_link_device(self, ntid):
        return self._get_bnode_link(ntid, idtype=wbuilder_util.IDTYPE_AUDIODEVICE)

    def _get_bnode_link_shareset(self, ntid):
        return self._get_bnode_link(ntid, idtype=wbuilder_util.IDTYPE_SHARESET)

    def _get_bnode_link(self, ntid, idtype=None):
        if not ntid:
            return None
        bank_id = ntid.get_root().get_id()
        tid = ntid.value()
        return self._get_bnode(bank_id, tid, idtype)

    # Finds a builder node from a bank+id ref
    def _get_bnode(self, bank_id, tid, idtype=None, nbankid_target=None):
        if bank_id <= 0  or tid <= 0:
            # bank -1 seen in KOF12 bgm's play action referencing nothing
            return

        node = self.__get_node(bank_id, tid, idtype)
        if node:
            bnode = self._init_bnode(node)
        else:
            bnode = None

        if not bnode:
            # May need to register info about missing node. Those are possible and common in Wwise, some rules:
            # - object hierarchy is always saved together (object > parents > parents)
            # - objects like switches/ranseqs can only use dirent children
            # - families are saved together in a bank (can't have one bank with children, another with parents)
            # - parent may reference missing children (unsure how wwise creates this, can't simulate with latest versions)
            # - objects may reference buses that aren't loaded in init.bnk
            #
            # Basically we have those types of calls:
            # - audio > audio: can be ignored (must be garbage, knowing regular objects go together)
            # - audio > bus: missing init.bnk
            # - action > audio: missing bnk with audio (one bank may save events, another audio)
            if idtype == wbuilder_util.IDTYPE_BUS:
                if (bank_id, tid) not in self._missing_nodes_buses:
                    logging.debug("generator: missing bus node %s in unknown bank", tid)

                self._missing_nodes_buses[(bank_id, tid)] = True

            elif nbankid_target:
                # when asked for a target bank (action): should exist
                if bank_id in self._loaded_banks:
                    if (bank_id, tid) not in self._missing_nodes_loaded: 
                        bankname = self._loaded_banks[bank_id]
                        logging.debug("generator: missing node %s in loaded bank %s", tid, bankname)

                    # bank is loaded: requested ID must be leftover garbage
                    self._missing_nodes_loaded[(bank_id, tid)] = True

                else:
                    bankname = nbankid_target.get_attr('hashname')
                    if not bankname:
                        bankname = str(nbankid_target.value())

                    if (bank_id, tid) not in self._missing_nodes_others:
                        logging.debug("generator: missing node %s in non-loaded bank %s", tid, bankname)

                    # bank not loaded: save bank name too
                    self._missing_nodes_others[(bank_id, tid)] = True
                    self._missing_banks[bankname] = True

            else:
                if (bank_id, tid) not in self._missing_nodes_unknown:
                    logging.debug("generator: missing other node %s in unknown bank", tid)

                # unknown if node is in other bank or leftover garbage
                self._missing_nodes_unknown[(bank_id, tid)] = True

        return bnode

    # Takes a parser "node" and makes a rebuilt "bnode" for txtp use.
    # Normally would only need to build per sid and ignore repeats (clones) in different banks, but
    # some games repeat sid for different objects in different banks (not clones), so just make one per node.
    def _init_bnode(self, node, mark_used=True):
        if not node:
            return None

        # check is node already in cache
        bnode = self._node_to_bnode.get(id(node))
        if bnode:
            return bnode

        # builder node with a helper class and save to cache
        # (some banks get huge and call the same things again and again, it gets quite slow to parse every time)
        hircname = node.get_name()
        bclass = wbuilder_util.get_builder_hirc_class(hircname)

        bnode = bclass()

        # Add bnode to list *before* building it
        #
        # In very rare cases, an auxbus sets OverrideBusId to a bus that also uses that same auxbus.
        # new _init_bnode auxbus > new _init_bnode bus > new _init_bnode auxbus > new ... (recursive exception).
        # Setting it now ensures bus gets the same (not-fully built) object reference and stops the recursion.
        # Not sure how Wwise handles it though.
        self._node_to_bnode[id(node)] = bnode

        bnode.init_builder(self)
        bnode.init_node(node)

        if mark_used:
            self._used_node[id(node)] = True #register usage for unused detection
        return bnode
