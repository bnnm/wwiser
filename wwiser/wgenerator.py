import logging, os

from wwiser import wgenerator_mover
from . import wgamesync, wrebuilder, wtxtp, wtxtp_util, wtxtp_cache
from . import wgenerator_filter, wgenerator_mediaindex, wgenerator_transitions, wgenerator_mover



# Tries to write .txtp from a list of HIRC objects. Each object parser adds some part to final
# .txtp (like output name, or text info) and calls child objects, 'leaf' node(s) being some 
# source .wem in CAkSound or CAkMusicTrack.
#
# Nodes that don't contribute to audio are ignored. Objects may depend on variables, but some
# games use SetState and similar events, while others change via API. To unify both cases
# .txtp are created per possible variable combination, or variables may be pre-set via args.
#
# Output name is normally from event name (or number, if not defined), or first object found.
# .wem names are not used by default (given there can be multiple and that's how wwise works).
# Names and other info is written in the txtp.

#******************************************************************************

class Generator(object):
    def __init__(self, banks):
        self._banks = banks

        self._rebuilder = wrebuilder.Rebuilder()
        self._txtpcache = wtxtp_cache.TxtpCache()
        self._mediaindex = wgenerator_mediaindex.MediaIndex(banks)

        # options
        self._generate_unused = False       # generate unused after regular txtp
        self._move = False                  # move sources to wem dir
        self._filter = wgenerator_filter.GeneratorFilter()  # filter nodes
        self._bank_order = False            # use bank order to generate txtp (instead of prioritizing named nodes)

        self._default_hircs = self._rebuilder.get_generated_hircs()
        self._filter.set_default_hircs(self._default_hircs)
        self._rebuilder.set_filter(self._filter)

        self._default_params = None

        self._moved_sources = {}            # ref

        self._object_sources = {
            'CAkSound': 'AkBankSourceData',
            'CAkMusicTrack': 'AkBankSourceData',
        }

    #--------------------------------------------------------------------------

    def set_filter(self, filter):
        self._filter.add(filter)

    def set_filter_rest(self, flag):
        self._filter.rest = flag

    def set_bank_order(self, flag):
        self._bank_order = flag

    def set_generate_unused(self, generate_unused):
        if not generate_unused:
            return
        self._generate_unused = generate_unused

    def set_move(self, move):
        if not move:
            return
        self._move = move

    def set_params(self, params):
        if params is None: #allow []
            return
        self._default_params = wgamesync.GamesyncParams(self._txtpcache)
        self._default_params.set_params(params)

    def set_gamevars(self, items):
        self._txtpcache.gamevars.add(items)

    def set_renames(self, items):
        self._txtpcache.renamer.add(items)

    #--------------------------------------------------------------------------

    def set_outdir(self, path):
        if path is None:
            return
        self._txtpcache.outdir = self._txtpcache.normalize_path(path)

    def set_wemdir(self, path):
        if path is None:
            return
        self._txtpcache.wemdir = self._txtpcache.normalize_path(path)

    def set_volume(self, volume):
        self._txtpcache.set_volume(volume)

    def set_lang(self, flag):
        self._txtpcache.lang = flag

    def set_name_wems(self, flag):
        self._txtpcache.name_wems = flag

    def set_name_vars(self, flag):
        self._txtpcache.name_vars = flag

    def set_bnkskip(self, flag):
        self._txtpcache.bnkskip = flag

    def set_bnkmark(self, flag):
        self._txtpcache.bnkmark = flag

    def set_alt_exts(self, flag):
        self._txtpcache.alt_exts = flag

    def set_dupes(self, flag):
        self._txtpcache.dupes = flag

    def set_dupes_exact(self, flag):
        self._txtpcache.dupes_exact = flag

    def set_random_all(self, flag):
        self._txtpcache.random_all = flag

    def set_random_multi(self, flag):
        self._txtpcache.random_multi = flag

    def set_random_force(self, flag):
        self._txtpcache.random_force = flag

    def set_write_delays(self, flag):
        self._txtpcache.write_delays = flag

    def set_silence(self, flag):
        self._txtpcache.silence = flag

    def set_tags(self, tags):
        self._txtpcache.tags = tags
        tags.set_txtpcache(self._txtpcache)

    def set_x_noloops(self, flag):
        self._txtpcache.x_noloops = flag

    def set_x_notxtp(self, flag):
        self._txtpcache.x_notxtp = flag

    def set_x_nameid(self, flag):
        self._txtpcache.x_nameid = flag

    #--------------------------------------------------------------------------

    def generate(self):
        try:
            logging.info("generator: start")

            self._setup()
            self._read_externals()
            self._write_main()
            self._write_unused()
            self._report()

        except Exception: # as e
            logging.warn("generator: PROCESS ERROR! (report)")
            logging.exception("")
            raise
        return

    def _report(self):
        reb = self._rebuilder
        txc = self._txtpcache
        mdi = self._mediaindex

        if self._filter.active and self._generate_unused and not self._filter.rest:
            logging.info("generator: NOTICE! can't generate unused when partially filtering nodes")

        if reb.has_unused() and not self._generate_unused:
            logging.info("generator: NOTICE! possibly unused audio? (find+load more banks?)")
            logging.info("*** set 'generate unused' option to include, may not create anything")

        if mdi.get_missing_media():
            missing = len(mdi.get_missing_media())
            logging.info("generator: WARNING! missing %s memory audio (load more banks?)", missing)

        if reb.get_missing_nodes_loaded():
            missing = len(reb.get_missing_nodes_loaded())
            logging.info("generator: WARNING! missing %s Wwise objects in loaded banks (ignore?)", missing)

        if reb.get_missing_nodes_others():
            missing = len(reb.get_missing_nodes_others())
            logging.info("generator: WARNING! missing %s Wwise objects in other banks (load?)", missing)
            for bankinfo in reb.get_missing_banks():
                logging.info("- %s.bnk" % (bankinfo))

        if reb.get_missing_nodes_unknown():
            missing = len(reb.get_missing_nodes_unknown())
            logging.info("generator: WARNING! missing %s Wwise objects in unknown banks (load/ignore?)", missing)

        if reb.get_multiple_nodes():
            missing = len(reb.get_multiple_nodes())
            logging.info("generator: WARNING! repeated %s Wwise objects in multiple banks (load less?)", missing)

        if not txc.created:
            logging.info("generator: WARNING! no .txtp were created (find+load banks with events?)")

        if reb.get_transition_objects():
            logging.info("generator: WARNING! transition object in playlists (report)")
        if reb.get_unknown_props():
            logging.info("generator: WARNING! unknown properties in some objects (report)")
            for prop in reb.get_unknown_props():
                logging.info("- %s" % (prop))

        if txc.trims:
            logging.info("generator: WARNING! trimmed %s long filenames (use shorter dirs?)", txc.trims)
            logging.info("*** set 'tags.m3u' option for shorter names + tag file with full names")

        if txc.multitrack and not self._default_params:
            logging.info("generator: multitracks detected (ignore, may generate in future versions)")

        dir = txc.get_txtp_dir()
        if not dir:
            dir = '.'

        if txc.streams and not self._move:
            logging.info("generator: some .txtp (%s) use streams, move to %s", txc.streams, dir)
        if txc.internals and not txc.bnkskip:
            logging.info("generator: some .txtp (%s) use .bnk, move to %s", txc.internals, dir)
            for bankname in txc.get_banks():
                logging.info("- %s", bankname)

        #logging.info("generator: done")
        line = "created %i" % txc.created
        if txc.duplicates:
            line += ", %i duplicates" % txc.duplicates
        if self._generate_unused:
            line += ", unused %i" % txc.unused
        logging.info("generator: done (%s)", line)


    def _setup(self):
        self._setup_nodes()
        self._mediaindex.load()
        return

    def _setup_nodes(self):
        mover_nodes = []
        for bank in self._banks:
            root = bank.get_root()
            bank_id = root.get_id()
            bankname = bank.get_root().get_filename()

            self._rebuilder.add_loaded_bank(bank_id, bankname)

            # register sids/nodes first since banks can point to each other
            items = bank.find(name='listLoadedItem')
            if not items: # media-only banks don't have items
                continue

            for node in items.get_children():
                name = node.get_name()
                nsid = node.find1(type='sid')
                if not nsid:
                    logging.info("generator: not found for %s in %s", name, bankname) #???
                    continue
                sid = nsid.value()

                self._rebuilder.add_node_ref(bank_id, sid, node)

                # for nodes that can contain sources save them to move later
                if self._move:
                    node_name = self._object_sources.get(name)
                    if node_name:
                        nsources = node.finds(name=node_name)
                        mover_nodes.extend(nsources)
        
        self._move_wems(mover_nodes)
        return

    def _write_main(self):
        # save nodes in bank order rather than all together (allows fine tuning bank load order)

        logging.info("generator: processing nodes")

        for bank in self._banks:
            self._write_bank(bank)
        return

    def _write_bank(self, bank):
        items = bank.find(name='listLoadedItem')
        if not items:
            return

        nodes_filtered = []
        nodes_named = []
        nodes_unnamed = []

        # save candidate nodes to generate
        nodes = items.get_children()
        for node in nodes:
            classname = node.get_name()
            nsid = node.find1(type='sid')
            if not nsid:
                continue
            #sid = nsid.value()

            generate = False

            if self._filter.active:
                generate = self._filter.generate_outer(node, nsid, classname=classname)

                if generate:
                    item = node
                    nodes_filtered.append(item)
                    continue
                else:
                    # ignore node if not in filter and not marked to include rest after filter
                    # (with flag would register valid non-filtered nodes below, written after filtered nodes)
                    if not self._filter.rest:
                        continue

            if not generate and classname in self._default_hircs:
                generate = True

            if not generate:
                continue

            # When making txtp, put named nodes in a list to generate first, then unnamed nodes.
            # Useful when multiple events do the same thing, but we only have wwnames for one
            # (others may be leftovers). This way named ones are generated and others are ignored
            # as dupes. Can be disabled to treat all as unnamed = in bank order.
            hashname = nsid.get_attr('hashname')
            if hashname and not self._bank_order:
                item = (hashname, node)
                nodes_named.append(item)
            else:
                item = (nsid.value(), node)
                nodes_unnamed.append(item)

        # prepare nodes in final order
        nodes = []
        nodes += nodes_filtered
        nodes_named.sort() # usually gives better results with dupes
        for __, node in nodes_named:
            nodes.append(node)
        for __, node in nodes_unnamed:
            nodes.append(node)
        logging.debug("generator: writting bank nodes (names: %s, unnamed: %s, filtered: %s)", len(nodes_named), len(nodes_unnamed), len(nodes_filtered))

        # make txtp for nodes
        for node in nodes:
            self._make_txtp(node)

    def _write_unused(self):
        if not self._generate_unused:
            return
        if not self._rebuilder.has_unused():
            return

        # when filtering nodes without 'rest' (i.e. only generating a few nodes) can't generate unused,
        # as every non-filtered node would be considered so (generate first then add to filter list?)
        if self._filter.active and not self._filter.rest:
            return

        logging.info("generator: processing unused")

        self._txtpcache.unused_mark = True
        #self._txtpcache.set_making_unused(True) #maybe set '(bank)-unused-(name) filename?

        for name in self._rebuilder.get_unused_names():
            nodes = self._rebuilder.get_unused_list(name)

            for node in nodes:
                self._make_txtp(node)

        self._txtpcache.unused_mark = False
        return

    def _make_txtp(self, node):
        # When default_params aren't set and objects need them, Txtp finds possible params, added
        # to "ppaths". Then, it makes one .txtp per combination (like first "music=b01" then ""music=b02")

        transitions = wgenerator_transitions.Transitions(node)

        try:
            # base .txtp
            txtp = wtxtp.Txtp(self._txtpcache, self._mediaindex, params=self._default_params, transitions=transitions)
            self._rebuilder.begin_txtp(txtp, node)

            ppaths = txtp.ppaths  # gamesync "paths" found during process
            if ppaths.empty:
                # single .txtp (no variables)
                txtp.write()
            else:
                # .txtp per variable combo
                combos = ppaths.combos()
                for combo in combos:
                    #logging.info("generator: combo %s", combo.elems)
                    txtp = wtxtp.Txtp(self._txtpcache, self._mediaindex, params=combo, transitions=transitions)
                    self._rebuilder.begin_txtp(txtp, node)
                    txtp.write()

            # triggers are handled a bit differently
            if ppaths.stingers:
                params = self._default_params #?
                for stinger in ppaths.stingers:
                    txtp = wtxtp.Txtp(self._txtpcache, self._mediaindex, params=params)
                    self._rebuilder.begin_txtp_stinger(txtp, stinger)
                    txtp.write()

            tr_nodes = transitions.get_nodes()
            if tr_nodes:
                self._txtpcache.transition_mark = True

                # handle transitions of current files (so filtered nodes don't appear)
                for ncaller, transition in tr_nodes:
                    txtp = wtxtp.Txtp(self._txtpcache, self._mediaindex, params=self._default_params)
                    self._rebuilder.begin_txtp(txtp, transition)
                    txtp.set_ncaller(ncaller)
                    txtp.write()

                #for ncaller, tnode in tr_nodes:
                #    self._make_txtp(tnode, ncaller=ncaller)
                self._txtpcache.transition_mark = False

        except Exception: #as e
            sid = 0
            bankname = '?'
            nsid = node.find1(type='sid')
            if nsid:
                sid = nsid.value()
                bankname = nsid.get_root().get_filename()

            logging.info("generator: ERROR! node %s in %s", sid, bankname)
            raise

        return

    #--------------------------------------------------------------------------

    def _read_externals(self):
        self._txtpcache.externals.load(self._banks)
        return

    def _move_wems(self, nodes):
        if not nodes:
            return
        mover = wgenerator_mover.Mover(self._txtpcache)
        mover.move_wems(nodes)
        return
