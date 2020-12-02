import logging, os, pkgutil, itertools
from . import wutil, wgamesync, wrebuilder, wtxtp, wtxtp_util


# Tries to write .txtp from a list of HIRC objects. Each object parser adds some part to final
# .txtp (like output name, or text info) and calls child objects, 'leaf' node(s) being some 
# source .wem in CAkSound or CAkMusicTrack.
#
# Nodes that don't contribute to audio are ignored. Some objects depend on variables, but some
# games use SetState and similar events, while others change via API. To unify both cases
# .txtp are created per possible variable combination, or variables may be pre-set via args.
#
# output name is normally from event name (or number, if not defined), or first object found.
# .wem names are not used by default (given there can be multiple and that's how wwise works).
# Names and other info is written in the txtp.

#******************************************************************************

class Generator(object):
    def __init__(self, banks):
        self._banks = banks

        self._rebuilder = wrebuilder.Rebuilder()
        self._txtpcache = wtxtp.TxtpCache()

        self._generate_unused = False
        self._move = False
        self._moved_sources = {}
        self._filter = []
        self._default_params = None

        self._object_sources = {
            'CAkSound': 'AkBankSourceData',
            'CAkMusicTrack': 'AkBankSourceData',
        }

    #--------------------------------------------------------------------------

    def set_filter(self, filter):
        if not filter:
            return
        self._filter += filter

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

    #--------------------------------------------------------------------------

    def get_dir(self):
        dir = ''
        if self._txtpcache.outdir:
            dir += self._txtpcache.outdir
        if self._txtpcache.wemdir:
            dir += self._txtpcache.wemdir
        return dir

    def _normalize_path(self, path):
        #path = path or '' #better?
        if path is None:
            path = ''
        path = path.strip()
        path = path.replace('\\', '/')
        if path and not path.endswith('/'):
            path += '/'
        return path

    def set_outdir(self, outdir):
        if outdir is None:
            return
        self._txtpcache.outdir = self._normalize_path(outdir)

    def set_wemdir(self, wemdir):
        if wemdir is None:
            return
        self._txtpcache.wemdir = self._normalize_path(wemdir)

    def set_volume(self, volume):
        if not volume:
            return
        try:
            percent = False
            if volume.lower().endswith('db'):
                volume = volume[:-2]
                self._txtpcache.volume_db = True
            elif volume.lower().endswith('%'):
                volume = volume[:-1]
                percent = True

            self._txtpcache.volume_master = float(volume)
            if percent:
                print(self._txtpcache.volume_master)
                self._txtpcache.volume_master = self._txtpcache.volume_master / 100.0
                print(self._txtpcache.volume_master)

            if self._txtpcache.volume_db:
                self._txtpcache.volume_decrease = (self._txtpcache.volume_master < 0)
            else:
                self._txtpcache.volume_decrease = (self._txtpcache.volume_master < 1.0)

        except:
            logging.info("generator: ignored incorrect volume")


    def set_lang(self, flag):
        self._txtpcache.lang = flag

    def set_wemnames(self, flag):
        self._txtpcache.wemnames = flag

    def set_bnkskip(self, flag):
        self._txtpcache.bnkskip = flag

    def set_bnkmark(self, flag):
        self._txtpcache.bnkmark = flag

    def set_alt_exts(self, flag):
        self._txtpcache.alt_exts = flag

    def set_dupes(self, flag):
        self._txtpcache.dupes = flag

    def set_random_all(self, flag):
        self._txtpcache.random_all = flag

    def set_random_force(self, flag):
        self._txtpcache.random_force = flag

    def set_x_nocrossfade(self, flag):
        self._txtpcache.x_nocrossfade = flag

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
            self._write()
            self._write_unused()
            self._write_transitions()
            self._report()

        except Exception: # as e
            logging.warn("generator: PROCESS ERROR! (report)")
            logging.exception("")
            raise
        return

    def _report(self):
        reb = self._rebuilder
        txc = self._txtpcache

        if reb.get_missing_media():
            logging.info("generator: WARNING! missing %i memory audio (load more banks?)" % (reb.get_missing_media()))
        if reb.get_missing_nodes():
            logging.info("generator: WARNING! missing %i Wwise objects (load more banks?)" % (reb.get_missing_nodes()))

        if reb.get_transition_objects():
            logging.info("generator: WARNING! transition object in playlists (report)")
        if reb.get_unknown_props():
            logging.info("generator: WARNING! unknown properties in some objects (report)")
            for prop in reb.get_unknown_props():
                logging.info("- %s" % (prop))

        if txc.trims:
            logging.info("generator: WARNING! trimmed %i long filenames (use shorter dirs?)" % (txc.trims))
        if txc.multitrack and not self._default_params:
            logging.info("generator: multitracks detected")

        dir = self.get_dir()
        if not dir:
            dir = '.'

        if txc.streams and not self._move:
            logging.info("generator: some .txtp (%i) use streams, move to %s" % (txc.streams, dir))
        if txc.internals and not txc.bnkskip:
            logging.info("generator: some .txtp (%i) use .bnk, move to %s" % (txc.internals, dir))
            for bankname in txc.get_banks():
                logging.info("- %s" % (bankname))

        #logging.info("generator: done")
        line = "created %i" % txc.created
        if txc.duplicates:
            line += ", %i duplicates" % txc.duplicates
        if self._generate_unused:
            line += ", unused %i" % txc.unused
        logging.info("generator: done (%s)" % (line))


    def _setup(self):
        for bank in self._banks:
            bankname = bank.get_root().get_filename()

            # register sids/nodes first since banks can point to each other
            items = bank.find(name='listLoadedItem')
            if items: # media-only banks don't have items
                for node in items.get_children():
                    name = node.get_name()
                    nsid = node.find1(type='sid')
                    if not nsid:
                        logging.info("generator: not found for %s in %s" % (name, bankname))
                        continue
                    sid = nsid.value()

                    self._rebuilder.add_node_ref(sid, node)

                    # move wems to folder for nodes that can contain sources
                    if self._move:
                        node_name = self._object_sources.get(name)
                        if node_name:
                            nsources = node.finds(name=node_name)
                            for nsource in nsources:
                                self._move_wem(nsource)

            # preload indexes for internal wems for bigger banks
            nindex = bank.find(name='MediaIndex')
            if nindex:
                nsids = nindex.finds(type='sid')
                for nsid in nsids:
                    sid = nsid.value()
                    attrs = nsid.get_parent().get_attrs()
                    index = attrs.get('index')
                    if index is not None:
                        self._rebuilder.add_media_index(bankname, sid, index)

        return


    def _write(self):
        default_hircs = self._rebuilder.get_generated_hircs()
        for bank in self._banks:
            items = bank.find(name='listLoadedItem')
            if not items:
                continue

            for node in items.get_children():
                name = node.get_name()

                #filter list
                generate = False
                if self._filter:
                    sid = node.find1(type='sid').value()
                    if   str(sid) in self._filter:
                        generate = True
                    elif name in self._filter:
                        generate = True
                else:
                    if name in default_hircs:
                        generate = True

                if not generate:
                    continue

                self._make_txtp(node)

        self._write_transitions()
        return

    def _write_transitions(self):
        if self._filter:
            return

        self._txtpcache.transition_mark = True
        for node in self._rebuilder.get_transition_segments():
            self._make_txtp(node)
        self._txtpcache.transition_mark = False
        self._rebuilder.empty_transition_segments() #restart for unused


    def _write_unused(self):
        if self._filter:
            return
        if not self._rebuilder.has_unused():
            return

        if not self._generate_unused:
            logging.info("generator: WARNING! possibly unused audio? (find+load more banks?)")
            logging.info("*** set 'generate unused' option to include, may not create anything")
            return

        logging.info("generator: processing unused")

        self._txtpcache.unused_mark = True
        #self._txtpcache.set_making_unused(True) #maybe set '(bank)-unused-(name) filename?
        for name in self._rebuilder.get_unused_names():
            for node in self._rebuilder.get_unused_list(name):
                self._make_txtp(node)
        self._txtpcache.unused_mark = False

        self._write_transitions()
        return

    def _make_txtp(self, node):
        # When params aren't set and objects need them, all possible params are added
        # to "paths" list. Then, instead of generating a giant .txtp it recreates one
        # per combination (like first "music=b01" then ""music=b02")

        try:
            params = wgamesync.GamesyncParams(self._txtpcache) #current config
            ppaths = wgamesync.GamesyncPaths(self._txtpcache)  #paths during process
            if self._default_params:            #external config
                params = self._default_params

            txtp = wtxtp.Txtp(params, ppaths, self._txtpcache, self._rebuilder)
            self._rebuilder.begin_txtp(txtp, node)

            if ppaths.empty:
                # without variables
                txtp.write()
            else:
                # per variable combo
                combos = ppaths.combos()
                for combo in combos:
                    #logging.info("generator: combo %s", combo.elems)
                    txtp = wtxtp.Txtp(combo, ppaths, self._txtpcache, self._rebuilder)
                    self._rebuilder.begin_txtp(txtp, node)
                    txtp.write()

            # triggers are handled a bit differently
            if ppaths.stingers:
                stingers = ppaths.stingers
                ppaths = wgamesync.GamesyncPaths(self._txtpcache)
                for stinger in stingers:
                    txtp = wtxtp.Txtp(params, ppaths, self._txtpcache, self._rebuilder)
                    self._rebuilder.begin_txtp_stinger(txtp, stinger)
                    txtp.write()

        except Exception: #as e
            sid = 0
            bankname = '?'
            nsid = node.find1(type='sid')
            if nsid:
                sid = nsid.value()
                bankname = nsid.get_root().get_filename()

            logging.info("generator: ERROR! node %s in %s" % (sid, bankname))
            raise

        return

    #--------------------------------------------------------------------------

    # Moves 123.wem to /txtp/wem/123.wem, or 123.ogg/logg to /txtp/wem/123.logg if alt_exts is set
    #todo cleanup (same as rebuilder)
    def _move_wem(self, node):
        if not node:
            return

        source = wtxtp_util.NodeSource(node, None)
        if not source or not source.tid: #?
            return
        if source.tid in self._moved_sources:
            return
        if source.plugin_external or source.plugin_id: #not audio:
            return
        if source.internal and not self._txtpcache.bnkskip:
            return

        self._moved_sources[source.tid] = True #skip dupes

        dir = self.get_dir()
        if self._txtpcache.lang:
            dir += source.subdir()

        nroot = node.get_root()
        in_dir = nroot.get_path()
        out_dir = in_dir
        if dir:
            out_dir = os.path.join(out_dir, dir)
            os.makedirs(out_dir, exist_ok=True)

        in_extension = source.extension
        out_extension = source.extension
        if self._txtpcache.alt_exts:
            #in_extension = source.extension_alt #handled below
            out_extension = source.extension_alt

        in_name = "%s.%s" % (source.tid, in_extension)
        in_name = os.path.join(in_dir, in_name)
        in_name = os.path.normpath(in_name)
        out_name = "%s.%s" % (source.tid, out_extension)
        out_name = os.path.join(out_dir, out_name)
        out_name = os.path.normpath(out_name)

        if os.path.exists(out_name):
            if os.path.exists(in_name):
                logging.info("generator: cannot move %s (exists on output folder)" % (in_name))
            return

        if not os.path.exists(in_name):
            bank = nroot.get_filename()
            if self._txtpcache.alt_exts:
                in_name = "%s.%s" % (source.tid, source.extension_alt)
                in_name = os.path.join(in_dir, in_name)
                in_name = os.path.normpath(in_name)
                if not os.path.exists(in_name):
                    logging.info("generator: cannot move %s (file not found) / %s" % (in_name, bank))
                    return
            else:
                logging.info("generator: cannot move %s (file not found) / %s" % (in_name, bank))
                return

        #todo: with alt-exts maybe could keep case, ex .OGG to .LOGG (how?)
        os.rename(in_name, out_name)
        return
