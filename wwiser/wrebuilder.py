import logging
from . import wtxtp_util
from . import wrebuilder_nodes as rn



# Takes the parsed bank nodes and rebuilds them to simpler objects with quick access
# for main useful (sound) attributes, and has helper functions to write TXTP

#******************************************************************************

class Rebuilder(object):
    def __init__(self):
        self._DEFAULT_CLASS = rn._CAkNone

        self._ref_to_node = {}              # bank + sid > parser node
        self._id_to_refs = {}               # sid > bank + sid list
        self._node_to_bnode = {}            # parser node > rebuilt node
        #self._node_to_ref = {}             # parser node > bank + sid

        self._missing_nodes_loaded = {}     # missing nodes that should be in loaded banks (event garbage left by Wwise)
        self._missing_nodes_others = {}     # missing nodes in other banks (even pointing to other banks)
        self._missing_nodes_unknown = {}    # missing nodes of unknown type
        self._multiple_nodes = {}           # nodes that exist but were loaded in multiple banks and can't decide which one is best

        self._loaded_banks = {}             # id of banks that participate in generating
        self._missing_banks = {}            # banks missing in the "others" list
        self._unknown_props = {}            # object properties that need to be investigated
        self._transition_objects = 0        # info for future support

        self._filter = None                 # used for inner node filtering
        self._root_node = None              # for info

        # after regular generation we want a list of nodes that weren't used, and
        # generate TXTP for them, but ordered by types since generating some types
        # may end up using other unused types
        self._used_node = {}                # marks which node_refs has been used
        self._hircname_to_nodes = {}        # registered types > list of nodes
        self._transition_nodes = {}         # transitions (separate to avoid counting as unused)

        self._generated_hircs =  [
            'CAkEvent',
            'CAkDialogueEvent',
        ]

        # only parsed hircs at the moment are those that contribute to .txtp
        self._hircs = {
            # base
            'CAkEvent': rn._CAkEvent,
            'CAkDialogueEvent': rn._CAkDialogueEvent,
            'CAkActionPlay': rn._CAkActionPlay,
            'CAkActionTrigger': rn._CAkActionTrigger,

            # not found, may need to do something with them
            'CAkActionPlayAndContinue': rn._CAkActionPlayAndContinue,
            'CAkActionPlayEvent': rn._CAkActionPlayEvent,

            # sound engine
            'CAkLayerCntr': rn._CAkLayerCntr,
            'CAkSwitchCntr': rn._CAkSwitchCntr,
            'CAkRanSeqCntr': rn._CAkRanSeqCntr,
            'CAkSound': rn._CAkSound,

            # music engine
            'CAkMusicSwitchCntr': rn._CAkMusicSwitchCntr,
            'CAkMusicRanSeqCntr': rn._CAkMusicRanSeqCntr,
            'CAkMusicSegment': rn._CAkMusicSegment,
            'CAkMusicTrack': rn._CAkMusicTrack,

            # others
            'CAkStinger': rn._CAkStinger,
            'CAkState': rn._CAkState,
            'CAkFxCustom': rn._CAkFxCustom, #similar to CAkFeedbackNode but config only (referenced in AkBankSourceData)

            #not useful
            #CAkActorMixer
            #CAkActionSetState
            #CAkAction*
            #CAkBus
            #CAkAuxBus
            #CAkFeedbackBus: accepts audio from regular sounds + creates rumble
            #CAkFeedbackNode: played like audio (play action) and has source ID, but it's simply a rumble generator
            #CAkAttenuation
            #CAkAudioDevice
            #CAkFxShareSet
            #CAkLFOModulator
            #CAkEnvelopeModulator
            #CAkTimeModulator
        }

        # ordered by priority (needed to generate unused)
        self._unused_hircs = [
            #'CAkEvent',
            #'CAkDialogueEvent',
            'CAkActionPlay',
            'CAkActionTrigger',

            'CAkActionPlayAndContinue',
            'CAkActionPlayEvent',

            'CAkLayerCntr',
            'CAkSwitchCntr',
            'CAkRanSeqCntr',
            'CAkSound',

            'CAkMusicSwitchCntr',
            'CAkMusicRanSeqCntr',
            'CAkMusicSegment',
            'CAkMusicTrack',
        ]

        return

    def set_filter(self, filter):
        self._filter = filter

    def get_missing_nodes_loaded(self):
        return self._missing_nodes_loaded

    def get_missing_nodes_others(self):
        return self._missing_nodes_others

    def get_missing_nodes_unknown(self):
        return self._missing_nodes_unknown

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

    def get_generated_hircs(self):
        return self._generated_hircs

    #--------------------------------------------------------------------------

    # info about loaded banks
    def add_loaded_bank(self, bank_id, bankname):
        self._loaded_banks[bank_id] = bankname

    #--------------------------------------------------------------------------

    # register a new node
    def add_node_ref(self, bank_id, sid, node):
        # Objects can be repeated when saved to different banks, and should be clones (ex. Magatsu Wahrheit, Ori ATWOTW).
        # Except sometimes they aren't, so we need to treat bank+id as separate things (ex. Detroit, Punch Out).
        # Doesn't seem allowed in Wwise but it's possible if devs manually load banks without conflicting ids.
        # ids may be in other banks though, so must also allow finding by single id

        ref = (bank_id, sid)
        #self._node_to_ref[id(node)] = ref

        if self._ref_to_node.get(ref) is not None:
            logging.debug("generator: ignored repeated bank %s + id %s", bank_id, sid)
            return
        self._ref_to_node[ref] = node

        if sid not in self._id_to_refs:
            self._id_to_refs[sid] = []
        self._id_to_refs[sid].append(ref)

        hircname = node.get_name()
        if hircname not in self._hircname_to_nodes:
            self._hircname_to_nodes[hircname] = []
        self._hircname_to_nodes[hircname].append(node)
        return

    def _get_node_by_ref(self, bank_id, sid):
        ref = (bank_id, sid)
        # find node in current bank
        node = self._ref_to_node.get(ref)
        # try node in another bank
        if not node:
            refs = self._id_to_refs.get(sid)
            if not refs:
                return None
            if len(refs) > 1:
                # could try to figure out if nodes are equivalent before reporting?
                logging.debug("generator: id %s found in multiple banks, not found in bank %s", sid, bank_id)
                self._multiple_nodes[sid] = True
            ref = refs[0]
            node = self._ref_to_node.get(ref)
        return node

    def add_transition_segment(self, ntid):
        # transition nodes in switches don't get used, register to generate at the end
        if not ntid:
            return

        bank_id = ntid.get_root().get_id()
        tid = ntid.value()
        if not tid:
            return

        node = self._get_node_by_ref(bank_id, tid)
        if not node:
            return

        #save transition and a list of 'caller' nodes (like events) for info later
        key = id(node)
        items = self._transition_nodes.get(key)
        if not items:
            callers = set()
            items = (node, callers)
        
        root_ntid = None
        if self._root_node:
            root_ntid = self._root_node.find1(type='sid')
        items[1].add(root_ntid)

        self._transition_nodes[key] = items
        __ = self._get_bnode(node) #force parse/register, but don't use yet
        return

    def get_transition_segments(self):
        return self._transition_nodes.values()

    def reset_transition_segments(self):
        self._transition_nodes = {}


    def has_unused(self):
        # find if useful nodes where used
        for hirc_name in self._unused_hircs:
            nodes = self._hircname_to_nodes.get(hirc_name, [])
            for node in nodes:
                if id(node) not in self._used_node:
                    name = node.get_name()
                    #remove some false positives
                    if name == 'CAkMusicSegment':
                        #unused segments may not have child nodes (silent segments are ignored)
                        bnode = self._get_bnode(node, mark_used=False)
                        if bnode and bnode.ntids:
                            return True
        return False

    def get_unused_names(self):
        return self._unused_hircs

    def get_unused_list(self, hirc_name):
        results = []
        nodes = self._hircname_to_nodes.get(hirc_name, [])
        for node in nodes:
            if id(node) not in self._used_node:
                results.append(node)
        return results

    #--------------------------------------------------------------------------

    # Finds a rebuild node from a bank+id ref
    def _get_bnode_by_ref(self, bank_id, tid, sid_info=None, nbankid_info=None):
        if bank_id <= 0  or tid <= 0:
            # bank -1 seen in KOF12 bgm's play action referencing nothing
            return

        node = self._get_node_by_ref(bank_id, tid)
        if node:
            bnode = self._get_bnode(node)
        else:
            bnode = None

        if not bnode:
            # register info about missing node

            if nbankid_info:
                # when asked for a target bank
                if bank_id in self._loaded_banks:
                    if (bank_id, tid) not in self._missing_nodes_loaded: 
                        bankname = self._loaded_banks[bank_id]
                        logging.debug("generator: missing node %s in loaded bank %s, called by %s", tid, bankname, sid_info)

                    # bank is loaded: requested ID must be leftover garbage
                    self._missing_nodes_loaded[(bank_id, tid)] = True

                else:
                    bankname = nbankid_info.get_attr('hashname')
                    if not bankname:
                        bankname = str(nbankid_info.value())

                    if (bank_id, tid) not in self._missing_nodes_others:
                        logging.debug("generator: missing node %s in non-loaded bank %s, called by %s", tid, bankname, sid_info)

                    # bank not loaded: save bank name too
                    self._missing_nodes_others[(bank_id, tid)] = True
                    self._missing_banks[bankname] = True

            else:
                if (bank_id, tid) not in self._missing_nodes_unknown:
                    logging.debug("generator: missing node %s in unknown bank, called by %s", tid, sid_info)

                # unknown if node is in other bank or leftover garbage
                self._missing_nodes_unknown[(bank_id, tid)] = True

        return bnode

    # Takes a parser "node" and makes a rebuilt "bnode" for txtp use.
    # Normally would only need to rebuild per sid and ignore repeats (clones) in different banks, but
    # some games repeat sid for different objects in different banks (not clones), so just make one per node.
    def _get_bnode(self, node, mark_used=True):
        if not node:
            return None

        # check is node already in cache
        bnode = self._node_to_bnode.get(id(node))
        if bnode:
            return bnode

        # rebuild node with a helper class and save to cache
        # (some banks get huge and call the same things again and again, it gets quite slow to parse every time)
        hircname = node.get_name()
        bclass = self._hircs.get(hircname, self._DEFAULT_CLASS)

        bnode = bclass()
        bnode.init_builder(self)
        bnode.init_node(node)

        self._node_to_bnode[id(node)] = bnode
        if mark_used:
            self._used_node[id(node)] = True #register usage for unused detection
        return bnode

    #--------------------------------------------------------------------------

    def begin_txtp(self, txtp, node):
        bnode = self._get_bnode(node)
        if not bnode:
            return

        self._root_node = node #info for transitions

        root_config = wtxtp_util.NodeConfig()
        txtp.begin(node, root_config)
        bnode._make_txtp(txtp)

        self._root_node = None #info for transitions
        return

    def begin_txtp_stinger(self, txtp, stinger):
        bnode = self._get_bnode(stinger.node) #sid is stinger.ntrigger.value()
        if not bnode:
            return

        # not correct since CAkStinger have no sid (same TriggerID can call different segments),
        # this is to show info
        bnode.sid = stinger.ntrigger.value()
        bnode.nsid = stinger.ntrigger
        bnode.ntid = stinger.ntid

        #self._process_next(ntid, txtp)
        root_config = wtxtp_util.NodeConfig()
        txtp.begin(stinger.node, root_config, nname=stinger.ntrigger, ntid=stinger.ntrigger, ntidsub=stinger.ntid)
        bnode._make_txtp(txtp)
        return
