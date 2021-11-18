import logging, os

from wwiser import wgamesync_silences
from . import wgamesync, wtxtp_tree, wtxtp_info, wtxtp_namer, wtxtp_printer, wversion

# Builds a TXTP tree from original CAkSound/etc nodes, recreated as a playlist to simplify generation.
#
# For example a path like this:
#   event > play > musicranseq > musicsegment > musictrack > 1.wem
#                  * sequence  |                * random   \ 2.wem
#                              > musicsegment > musictrack > 3.wem
#                              |              \ musictrack > 4.wem
#                              > musicsegment > musictrack > 5.wem (0..10)
#                  * loop=inf  > musicsegment > musictrack > 5.wem (10..150)
#
# Internally may become (roughly):
# (root)
#   group (layered) #event
#       group (segmented) #musicranseq
#           group (random)
#               1.wem
#               2.wem
#           group (layered)
#               3.wem
#               4.wem
#           group (segmented)
#               5.wem (0..10s)
#           group (segmented)
#               5.wem (10s..150s)
#
# And could be simplified and written like:
#     1.wem
#     2.wem
#    group = -R2
#     3.wem
#     4.wem
#    group = -L2
#    5.wem #b 10.0
#    5.wem #b 160.0 #r 10.0
#  group = -S4 #@loop

#******************************************************************************

class Txtp(object):

    def __init__(self, txtpcache, rebuilder, params=None):
        self.params = params  #current gamesync "path" config (default/empty means must find paths)
        self.ppaths = wgamesync.GamesyncPaths(txtpcache)  #gamesync paths and config found during process
        self.spaths = wgamesync_silences.SilencePaths() #states used to mute tracks
        self.txtpcache = txtpcache
        self.rebuilder = rebuilder
        self.info = wtxtp_info.TxtpInfo(txtpcache)  # node info to add in output as comment

        # config during printing
        self.selected = None        # current random selection in sub-txtp
        self.sparams = None         # current silence combo in sub-txtp
        self.external_path = None   # current external
        self.external_name = None   # current external

        # for info
        self._namer = wtxtp_namer.TxtpNamer(self)
        self._callers = None
        return

    # start of txtp generation
    def begin(self, node, root_config, nname=None, ntid=None, ntidsub=None):
        # tree
        self._root = wtxtp_tree.TxtpNode(None, root_config)
        self._current = self._root

        # for names
        if not ntid:
            ntid = node.find1(type='sid')
        self._namer.update_config(node, nname, ntid, ntidsub)

        self._basepath = node.get_root().get_path()

        return

    #--------------------------------------------------------------------------

    def set_callers(self, callers):
        self._callers = callers
        self._namer.callers = callers

    def write(self):
        printer = wtxtp_printer.TxtpPrinter(self, self._root)
        printer.prepare() #simplify tree

        # may have files but all silent
        if not printer.has_sounds():
            return

        # write chains
        self._write_externals(printer)
        return

    def _write_externals(self, printer):

        # in case of externals, we can preload a .txt file that maps event tid > N paths
        # then a .txtp per external will be created
        if printer.has_externals and self.txtpcache.externals:
            # get external IDs #todo for now only one
            if len(printer.externals) > 1:
                logging.warn("generator: ignoring multiple externals (report)")
                elems = None
            else:
                elems = self.txtpcache.externals.get(printer.externals[0], None)

            if elems: # has external for current id, otherwise just go normally
                for elem in elems:
                    self.external_path = elem
                    self.external_name = os.path.splitext(os.path.basename(elem))[0]
                    self._write_selectable(printer)
                return

        self._write_selectable(printer)

    def _write_selectable(self, printer):
        # make one txtp per random/selectable group
        # selectable is only set if appropriate flags are defined
        if printer.selectable_count:
            count = printer.selectable_count
            # make one .txtp per random
            for i in range(1, count + 1):
                self.selected = i
                self._write_combos(printer)

        else:
            # make main .txtp
            self._write_combos(printer)

    def _write_combos(self, printer):
        # handle sub-txtp per silence combo
        if self.spaths.empty:
            # without variables
            self._write_txtp(printer)

        else:
            # per combo
            combos = self.spaths.combos()
            for combo in combos:
                self.sparams = combo
                self._write_txtp(printer)

            self.sparams = None

            # generate a base .txtp with all songs in some cases
            # - multiple states used like a switch, base playing everything = bad (MGR, Bayo2)
            # - singe state used for on/off a single layer, base playing everything = good (AChain)
            if len(combos) == 1:
                self._write_txtp(printer)

    def _write_txtp(self, printer):
        # Some games have GS combos and events that end up being the same (ex. Nier Automata, Bayonetta 2).
        # We make the txtp text and check (without comments) if wasn't already generated = dupe = ignored.
        # Because some txtp are 99% the same save minor differences (volumes, delays), those diffs should
        # be ignored, meaning text for checking and text for printing is slightly different
        # (this can be disabled so only exact dupes are printed).

        # make txtp + txtp for dupe checking
        text = printer.generate()
        if self.txtpcache.dupes_exact:
            # only considers dupes exact repeats
            texthash = hash(text)
        else:
            # by default uses a simpler text ignoring minor differences
            text_simpler = printer.generate(simpler=True)
            texthash = hash(text_simpler)

        # get name and check hash
        is_new = self.txtpcache.register_txtp(texthash, printer)
        name = self._namer.get_longname(printer, is_new)
        if not is_new and not self.txtpcache.dupes:
            logging.debug("txtp: ignore '%s' (repeat of %s)", name, texthash)
            return False

        # get final name, that may be changed/shorter depending on config
        longname = name + '.txtp'  #save full name in case it's cut to print in info
        name = self._namer.clean_name(name)
        logging.debug("txtp: saving '%s' (%s)", name, texthash)

        outdir = self.txtpcache.outdir
        if outdir:
            outdir = os.path.join(self._basepath, outdir)
            os.makedirs(outdir, exist_ok=True)

        outname = self._namer.get_outname(name, outdir)
        info = self._get_info(name, longname, printer)

        if self.txtpcache.x_notxtp:
            return

        with open(outname, 'w', encoding='utf-8') as outfile:
            outfile.write(text)
            outfile.write(info)
        return

    #--------------------------------------------------------------------------

    def group_random_continuous(self, elems, config):
        if not elems:
            return
        return self._group_add(config).random_continuous()

    def group_random_step(self, elems, config):
        if not elems:
            return
        return self._group_add(config).random_step()

    def group_sequence_continuous(self, elems, config):
        if not elems:
            return
        return self._group_add(config).sequence_continuous()

    def group_sequence_step(self, elems, config):
        if not elems:
            return
        return self._group_add(config).sequence_step()

    def group_layer(self, elems, config):
        if not elems:
            return
        return self._group_add(config).layer()

    def group_single(self, config, transition=None):
        return self._group_add(config).single(transition)

    def group_done(self, elems=None):
        if elems is not None and not elems: #to avoid unbalanced tree if added group has 0 elems
            return
        self._current = self._current.parent
        return self._current

    def source_sound(self, sound, config):
        return self._source_add(sound, config)

    def _group_add(self, config):
        node = wtxtp_tree.TxtpNode(self._current, config=config)

        self._current.append(node)
        self._current = node
        return node

    def _source_add(self, sound, config):
        node = wtxtp_tree.TxtpNode(self._current, sound=sound, config=config)
        self._current.append(node)
        return self._current

    #--------------------------------------------------------------------------

    def _get_info(self, name, longname, printer):

        # base info
        info  = '\n\n'
        info += '# AUTOGENERATED WITH WWISER %s\n' % (wversion.WWISER_VERSION)
        info += '#\n'
        info += '# %s\n' % (name)

        # config
        if longname and longname != name:
            info += '# * full name: %s\n' % (longname)

        gs_s = self.info.get_gsnames(False)
        gs_l = self.info.get_gsnames(True)
        if gs_s != gs_l:
            info += '# * full vars: %s\n' % (gs_l)

        if self.txtpcache.gamevars.active and printer.gamevars:
            info += '# * gamevars: %s\n' % (self.txtpcache.gamevars.get_info())

        if self._callers:
            info += '# * callers:\n'
            for caller in self.info.get_callers(self._callers):
                info += '# - %s\n' % (caller)

        if self.txtpcache.volume_master:
            info += '# * master volume: %sdB\n' % (self.txtpcache.volume_master)
        if self.txtpcache.volume_master_auto:
            info += '# * master volume: auto\n'

        if self.selected:
            extra = ''
            if self.txtpcache.random_force:
                extra = ' (forced)'
            elif self.txtpcache.random_multi:
                extra = ' (multi)'
            info += '# * selected group=%s%s\n' % (self.selected, extra)

        #bank info
        banks = self.info.get_banks()
        #info += '#\n'
        #info += '# Banks:\n'
        for bank in banks:
            info += '# - %s\n' % (bank)

        # tree info
        info += '#\n'
        lines = self.info.get_lines()
        info += ''.join(lines)


        return info
