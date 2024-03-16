import logging, os
from ... import wversion
from . import hnode_misc, wtxtp_tree, wtxtp_info, wtxtp_namer, wtxtp_printer

# Helds a TXTP tree from original CAkSound/etc nodes, recreated as a playlist to simplify generation.
# 'Renderer' code follows the path, while this has the redone playlist, that is then further simplified.
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

    def __init__(self, txtpcache):
        self.txtpcache = txtpcache
        self.info = wtxtp_info.TxtpInfo(txtpcache)  # node info to add in output as comment

        # config during printing
        self.selected = None        # current random selection in sub-txtp
        self.scparams_make_default = False #TODO improve
        self.external_path = None   # current external
        self.external_name = None   # current external

        # tree
        self._troot = None
        self._current = None

        # for info
        self._node = None
        self._namer = wtxtp_namer.TxtpNamer(self)
        return

    # start of txtp generation
    def begin(self, node, root_config):
        # tree
        self._troot = wtxtp_tree.TxtpNode(None, root_config)
        self._current = self._troot

        # for names
        self._node = node
        ntid = node.find1(type='sid')
        self._namer.node = node
        self._namer.ntid = ntid

        return

    #--------------------------------------------------------------------------

    def set_ncaller(self, ncaller):
        self._namer.ncaller = ncaller

    def set_bstinger(self, bstinger):
        self._namer.bstinger = bstinger

    def set_btransition(self, btransition):
        self._namer.btransition = btransition


    # write main .txtp
    # Sometimes there are multiple small variations with the same .txtp tree, in those cases 
    # we don't need to re-render and just create multiple sub-txtp with different settings here.
    def write(self):
        if not self._troot: #empty txtp (in rare cases)
            return
        printer = wtxtp_printer.TxtpPrinter(self, self._troot)
        printer.prepare() #simplify tree

        # may have files but all silent
        if not printer.has_sounds():
            return

        # write chains
        self._write_externals(printer)
        return

    # in case of externals, we can preload a .txt file that maps event tid > N paths
    # then a .txtp per external will be created
    def _write_externals(self, printer):

        if printer.has_externals and self.txtpcache.externals.active:
            # get external IDs
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

    # make one txtp per random/selectable group
    # selectable is only set if appropriate flags are defined
    def _write_selectable(self, printer):
        if printer.selectable_count:
            count = printer.selectable_count
            # make one .txtp per random
            for i in range(1, count + 1):
                self.selected = i
                self._write_txtp(printer)
            return

        self._write_txtp(printer)

    # main write
    def _write_txtp(self, printer):
        # Some games have GS combos and events that end up being the same (ex. Nier Automata, Bayonetta 2).
        # We make the txtp text and check (without comments) if wasn't already generated = dupe = ignored.
        # Because some txtp are 99% the same save minor differences (volumes, delays), those diffs should
        # be ignored, meaning text for checking and text for printing is slightly different
        # (this can be disabled so only exact dupes are printed).

        # make txtp + hash for dupe checking
        text = printer.generate()
        if self.txtpcache.dupes_exact:
            # only considers dupes exact repeats
            texthash = hash(text)
        else:
            # by default uses a simpler text ignoring minor differences
            text_simpler = printer.generate(simpler=True)
            texthash = hash(text_simpler)

        # final name (sans dupe mark)
        name = self._namer.get_longname(printer)

        # dupe check
        is_newtxtp = self.txtpcache.stats.register_txtp(texthash, printer)

        # Same name but different base node/bank is considered a "new name". Rarely happens when banks repeat events ids
        # that are actually different (name fixed in clean_name to avoid overwritting). It may also happen when passing
        # variable combos that repeat paths (base name) but same base bank/node (= useless "fake dupe".
        is_newname = self.txtpcache.stats.register_namenode(name, self._node)

        if not is_newtxtp and not is_newname: # fake dupe
            self.txtpcache.stats.unregister_dupe(texthash)
            return

        if not is_newtxtp and not self.txtpcache.dupes: #regular dupe
            if is_newname:
                logging.debug("txtp: ignore '%s' (repeat of %s)", name, texthash)
            return False
        
        if not is_newtxtp: # dupe mark
            name = self._namer.get_dupename(name)

        # get final name, that may be changed/shorter depending on config
        longname = name + '.txtp'  #save full name in case it's cut to print in info
        name = self._namer.clean_name(name)
        if self.txtpcache.renamer.skip:
            return
        logging.debug("txtp: saving '%s' (%s)", name, texthash)
        if self.txtpcache.no_txtp:
            return

        # prepare dirs and final output
        outdir = self.txtpcache.locator.get_txtp_fullpath(self._node)
        if outdir:
            os.makedirs(outdir, exist_ok=True)

        outname = self._namer.get_outname(name, outdir)
        info = self._get_info(name, longname, printer)

        with open(outname, 'w', encoding='utf-8') as outfile:
            outfile.write(text)
            outfile.write(info)
        return

    #--------------------------------------------------------------------------
    # txtp helpers, register a type of group/sound during "rendering".

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

    def group_single(self, config):
        return self._group_add(config).single()

    def group_done(self, elems=None):
        if elems is not None and not elems: #to avoid unbalanced tree if added group has 0 elems
            return
        self._current = self._current.parent
        return self._current

    def source_sound(self, sound, config):
        return self._source_add(sound, config)

    def _group_add(self, config):
        if not config:
            config = hnode_misc.NodeConfig()
        tnode = wtxtp_tree.TxtpNode(self._current, config=config)

        self._current.append(tnode)
        self._current = tnode
        return tnode

    def _source_add(self, sound, config):
        if not config:
            config = hnode_misc.NodeConfig()
        tnode = wtxtp_tree.TxtpNode(self._current, sound=sound, config=config)
        self._current.append(tnode)
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

        #gs_used_s = self.info.get_gsnames(False)
        gs_used_l = self.info.get_gsnames(True)
        if gs_used_l: #gs_used_s != gs_used_l:
            info += '# * gamesyncs: %s\n' % (gs_used_l.strip())

        sc_used = self.info.get_scnames()
        if sc_used:
            info += '# * statechunks: %s\n' % (sc_used)

        gv_used = self.info.get_gvnames()
        if gv_used:
            info += '# * gamevars: %s\n' % (gv_used)

        if self.txtpcache.volume_master:
            info += '# * master volume: %sdB\n' % (self.txtpcache.volume_master)
        if self.txtpcache.volume_master_auto:
            db = printer.volume_auto or 0.0
            if db == -0.0:
                db = 0.0
            info += '# * master volume: auto (%sdB)\n' % (db)

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
        path_lines = self.info.get_tree_lines()
        if path_lines:
            info += '#\n'
            info += ''.join(path_lines)

        sc_lines = self.info.get_statechunk_lines()
        if sc_lines:
            info += '#\n'
            info += ''.join(sc_lines)

        gv_lines = self.info.get_gamevar_lines()
        if gv_lines:
            info += '#\n'
            info += ''.join(gv_lines)


        return info
