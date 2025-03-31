import logging
from . import wfilter, wmover, wtxtp_cache, wreport
from .render import wbuilder, wrenderer, wstate, wglobalsettings
from ..parser import wdefs
from . import wlang



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
    def __init__(self, banks, locator, wwnames=None):
        self._banks = banks #BEWARE this will be pre-processed

        self._globalsettings = wglobalsettings.GlobalSettings()
        self._builder = wbuilder.Builder(self._globalsettings)
        self._txtpcache = wtxtp_cache.TxtpCache()
        self._ws = wstate.WwiseState(self._txtpcache)
        self._filter = wfilter.GeneratorFilter()  # filter nodes
        self._renderer = wrenderer.Renderer(self._txtpcache, self._builder, self._ws, self._filter)
        self._mover = wmover.Mover(self._txtpcache)

        self._txtpcache.locator = locator
        self._txtpcache.wwnames = wwnames
        self._txtpcache.externals.set_locator( locator )

        # options
        self._generate_unused = False       # generate unused after regular txtp
        self._move = False                  # move sources to wem dir
        self._bank_order = False            # use bank order to generate txtp (instead of prioritizing named nodes)

        self._default_hircs = self._renderer.get_generated_hircs()
        self._filter.set_default_hircs(self._default_hircs)

    #--------------------------------------------------------------------------

    def set_filter(self, filter):
        self._filter.add(filter)

    def set_filter_rest(self, flag):
        self._filter.generate_rest = flag

    def set_filter_normal(self, flag):
        self._filter.skip_normal = flag

    def set_filter_unused(self, flag):
        self._filter.skip_unused = flag

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

    def set_gamesyncs(self, items):
        self._ws.set_gsdefaults(items)

    def set_statechunks(self, items):
        self._ws.set_scdefaults(items)

    def set_gamevars(self, items):
        self._ws.set_gvdefaults(items)

    def set_renames(self, items):
        self._txtpcache.renamer.add(items)

    def set_statechunks_sd(self, flag):
        self._txtpcache.statechunks_skip_default = flag

    def set_statechunks_su(self, flag):
        self._txtpcache.statechunks_skip_unreachables = flag

    #--------------------------------------------------------------------------

    def set_master_volume(self, volume):
        self._txtpcache.set_master_volume(volume)

    def set_lang(self, elem):
        self._txtpcache.lang = elem

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

    def set_x_silence(self, flag):
        self._txtpcache.x_silence_all = flag

    def set_x_include_fx(self, flag):
        self._txtpcache.x_include_fx = flag

    def set_x_prefilter_paths(self, flag):
        self._txtpcache.x_prefilter_paths = flag

    def set_x_noloops(self, flag):
        self._txtpcache.x_noloops = flag

    def set_x_nameid(self, flag):
        self._txtpcache.x_nameid = flag

    def set_tags(self, tags):
        self._txtpcache.tags = tags  # registers short > long event names

    #--------------------------------------------------------------------------

    def _prepare(self):
        self._prepare_lang()
        self._prepare_banks()

    def _prepare_lang(self):
        # info
        if self._txtpcache.lang:
            info = self._txtpcache.lang
            logging.info("generator: selected localized bank '%s'", info)
        else:
            langs = wlang.Langs(self._banks, localized_only=True)
            if len(langs.items) > 1: #maybe should only print >1?
                logging.info("generator: multiple localized banks, will use first language")
                #info = ", ".join(f"{lang[0]} [{lang[1]}]" for lang in langs.items)
                for fullname, shortname in langs.items:
                    logging.info(f"- {fullname} [{shortname}]")
                self._txtpcache.lang = langs.items[0][0]

    def _prepare_banks(self):
        # removes localized banks of other langs, to avoid processing (would count as dupes)

        banks = []
        for bank in self._banks:
            root = bank.get_root()
            bankname = root.get_filename()
            bankpath = root.get_path()

            if self._txtpcache.lang:
                lang = wlang.Lang(bank)
                if not lang.matches(self._txtpcache.lang):
                    logging.debug("generator: ignored %s lang in %s/%s", lang.fullname, bankpath, bankname)
                    continue
            banks.append(bank)

        self._banks = banks

    #--------------------------------------------------------------------------

    def generate(self):
        try:
            logging.info("generator: start")
            self._prepare()

            self._setup()
            self._write_normal()
            self._write_unused()
            self._report()

        except Exception: # as e
            logging.warn("generator: PROCESS ERROR! (report)")
            logging.exception("")
            raise
        return

    def _report(self):
        wreport.Report(self).report()


    def _setup(self):
        self._setup_nodes()
        self._txtpcache.externals.load()
        return

    def _setup_nodes(self):

        # register nodes first since banks can point to each other
        for bank in self._banks:
            root = bank.get_root()
            version = root.get_version()
            bank_id = root.get_id()
            bankname = root.get_filename()

            if version in wdefs.partial_versions:
                logging.warning("generator: WARNING, ignored unsupported bank version %s (can't make .txtp)", version)
                continue

            self._builder.add_loaded_bank(bank_id, bankname)

            for nchunk in root.get_children():
                chunkname = nchunk.get_name()

                if chunkname == 'MediaIndex':
                    self._txtpcache.mediaindex.load(nchunk)

                elif chunkname == 'GlobalSettingsChunk':
                    self._globalsettings.load(nchunk)

                elif chunkname == 'HircChunk':
                    items = bank.find(name='listLoadedItem')
                    if not items: # media-only banks don't have items
                        continue

                    # HIRC node order is semi-fixed following these rules:
                    # - devices xN > buses xN > audio hierarchy (sound or music) xN > action+event xN
                    #   (all audio, then all action+events)
                    # - bus objects are saved as parent > children
                    # - audio objects are saved as childen > parent:
                    # - objects are ordered by parent's sid
                    #   (basically orders object tree but writes leafs first)
                    # - banks can contain only certain objects (manually selected) but always include parents
                    #   (can't have a musictrack without its musicsegment)
                    # - banks may also manually include bus hierarchy, that init.bnk also has, repeating them
                    # - example:
                    #     master-bus                3803692087
                    #         bus                   1983303249
                    #     bus                       714721605
                    #     musictrack                923536282
                    #         musicsegment          1065645898
                    #             musicranseq       715118501
                    #     aksound                   831435981
                    #         ranseq                874844450
                    #         aksound               81651614
                    #             actor-mixer       1004834203
                    #     ...
                    #     playaction                1058420436
                    #         event                 123597788
                    #     playaction                1018786158
                    #         event                 1317523067
                    #
                    # So might as well be random.

                    for node in items.get_children():
                        nsid = node.find1(type='sid')
                        if not nsid:
                            hircname = node.get_name()
                            logging.info("generator: not found for %s in %s", hircname, bankname) #???
                            continue
                        sid = nsid.value()

                        self._builder.register_node(bank_id, sid, node)

                        # for nodes that can contain sources save them to move later
                        if self._move:
                            self._mover.add_node(node)

        self._move_wems()
        return
   

    def _write_normal(self):
        # save nodes in bank order rather than all together (allows fine tuning bank load order)

        logging.info("generator: processing nodes")

        self._txtpcache.no_txtp = self._filter.skip_normal

        for bank in self._banks:
            self._write_bank(bank)

        self._txtpcache.no_txtp = False
        return

    def _write_bank(self, bank):
        items = bank.find(name='listLoadedItem')
        if not items:
            return

        nodes_allow = []
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

            # how nodes are accepted:
            # - filter not active: accept certain objects, and put them into named/unnamed lists (affects dupes)
            # - filter is active: accept allowed objects only, and put non-accepted into named/unnamed if "rest" flag is set (lower priority)
            allow = False
            if self._filter.active:
                allow = self._filter.allow_outer(node, nsid, classname=classname)
                if allow:
                    nodes_allow.append(node)
                    continue
                elif not self._filter.generate_rest:
                    continue # ignore non-"rest" nodes
                else:
                    pass #rest nodes are clasified below

            # include non-filtered nodes, or filtered but in rest
            if not allow and classname in self._default_hircs:
                allow = True

            if not allow:
                continue

            # put named nodes in a list to generate first, then unnamed nodes.
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
        nodes += nodes_allow

        # usually gives better results with dupes
        # older python(?) may choke when trying to sort name+nodes, set custom handler to force hashname only
        nodes_named.sort(key=lambda x: x[0] )

        for __, node in nodes_named:
            nodes.append(node)
        for __, node in nodes_unnamed:
            nodes.append(node)

        logging.debug("generator: writting bank nodes (names: %s, unnamed: %s, filtered: %s)", len(nodes_named), len(nodes_unnamed), len(nodes_allow))

        # make txtp for nodes
        for node in nodes:
            logging.debug("node: %s", node.find1(type='sid').value())
            self._render_txtp(node)

        return

    def _write_unused(self):
        if not self._generate_unused:
            return
        if not self._builder.has_unused():
            return

        # when filtering nodes without 'rest' (i.e. only generating a few nodes) can't generate unused,
        # as every non-filtered node would be considered so (generate first then add to filter list?)
        #if self._filter.active and not self._filter.generate_rest:
        #    return

        logging.info("generator: processing unused")
        if self._filter.active and not self._filter.generate_rest and not self._filter.has_unused():
            logging.info("generator: NOTICE! when using 'normal' filters must add 'unused' filters")

        self._txtpcache.no_txtp = self._filter.skip_unused
        self._txtpcache.stats.unused_mark = True

        for name in self._builder.get_unused_names():
            nodes = self._builder.get_unused_list(name)

            for node in nodes:

                allow = True
                if self._filter.active:
                    allow = self._filter.allow_unused(node)
                    #if self._filter.generate_rest: #?
                    #    allow = True

                if not allow:
                    continue

                self._render_txtp(node)

        self._txtpcache.stats.unused_mark = False
        self._txtpcache.no_txtp = False
        return


    # TXTP GENERATION
    # By default generator tries to make one .txtp per event. However, often there are multiple alts per
    # event that we want to generate:
    # - combinations of gamesyncs (states/switches)
    # - combinations of states in statechunks
    # - combinations of rtpc values
    # - variations of "selectable" wems (random1, then random2, etc)
    # - variations of externals that programmers can use to alter .wem on realtime
    # - transitions/stingers that could apply to current event
    # Generator goes step by step making combos of combos to cover all possible .txtp so the totals can be
    # huge (all those almost never happen at once).
    #
    # Base generation is "rendered" from current values, following Wwise's internals untils it creates a
    # rough tree that looks like a TXTP. This "rendering" varies depending on Wwise's internal state, meaning
    # you need to re-render when this state is different ('combinations'), as the objects it reaches change.
    # Changes that don't depend on state and that could be done by editting a .txtp manually are done 
    # post-rendering ('variations').
    #
    # Code below handles making 'combinations' (by chaining render_x calls), while code in Txtp handles
    # all 'variations' (by chaining write_x calls)

    def _render_txtp(self, node):
        try:
            self._renderer.render_node(node)

        except Exception: #as e
            sid = 0
            bankname = '?'
            nsid = node.find1(type='sid')
            if nsid:
                sid = nsid.value()
                bankname = nsid.get_root().get_filename()

            logging.info("generator: ERROR! node %s in %s", sid, bankname)
            raise

    #--------------------------------------------------------------------------

    def _move_wems(self):
        if not self._move:
            return

        self._mover.move_wems()
        return
