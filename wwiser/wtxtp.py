import logging, os
from . import wgamesync, wtxtp_tree, wtxtp_info, wversion


DEFAULT_OUTDIR = 'txtp/'
DEFAULT_WEMDIR = 'wem/'

#use a bit less than 255 so files can be moved around dirs
#long paths can be enabled on Windows but detection+support is messy...
WINDOWS_MAX_PATH = 235
WINDOWS_INTERNAL_NAME = 'nt'

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
#  group = -S4
#
#  loop_mode = auto #last segment

#******************************************************************************

class TxtpCache(object):
    def __init__(self):
        # process config
        self.outdir = DEFAULT_OUTDIR
        self.wemdir = DEFAULT_WEMDIR
        self.wemnames = False
        self.volume_master = None
        self.volume_db = False
        self.volume_decrease = False
        self.lang = False
        self.bnkmark = False
        self.bnkskip = False
        self.alt_exts = False
        self.dupes = False
        self.dupes_exact = False
        self.random_all = False
        self.random_force = False
        self.tagsm3u = False
        self.silence = False

        self.x_noloops = False
        self.x_notxtp = False
        self.x_nameid = False

        # process info
        self.created = 0
        self.duplicates = 0
        self.unused = 0
        self.multitrack = 0
        self.trims = 0
        self.streams = 0
        self.internals = 0
        self.names = 0

        # other helpers
        self.is_windows = os.name == WINDOWS_INTERNAL_NAME
        self.basedir = os.getcwd()

        self._txtp_hashes = {}
        self._name_hashes = {}
        self._banks = {}

        self._tag_names = {}

        self.transition_mark = False
        self.unused_mark = False


    def register_txtp(self, texthash, printer):
        if texthash in self._txtp_hashes:
            self.duplicates += 1
            return False

        self._txtp_hashes[texthash] = True
        self.created += 1
        if self.unused_mark:
            self.unused += 1

        if printer.has_internals():
            self.internals += 1
        if printer.has_streams():
            self.streams += 1
        return True

    def register_name(self, name):
        hashname = hash(name)

        self.names += 1
        if hashname in self._name_hashes:
            return False

        self._name_hashes[hashname] = True
        return True


    def register_bank(self, bankname):
        self._banks[bankname] = True
        return

    def get_banks(self):
        return self._banks

    def get_tag_names(self):
        return self._tag_names

#******************************************************************************

class Txtp(object):
    # info
    CLASSNAME_SHORTNAMES = {
            'CAkEvent': 'event',
            'CAkDialogueEvent': 'dialogueevent',
            'CAkActionPlay': 'action',
            'CAkActionPlayEvent': 'action',
            'CAkActionTrigger': 'action',

            'CAkLayerCntr': 'layer',
            'CAkSwitchCntr': 'switch',
            'CAkRanSeqCntr': 'ranseq',
            'CAkSound': 'sound',

            'CAkMusicSwitchCntr': 'musicswitch',
            'CAkMusicRanSeqCntr': 'musicranseq',
            'CAkMusicSegment': 'musicsegment',
            'CAkMusicTrack': 'musictrack',

            #'CAkStinger': 'stinger',
    }

    def __init__(self, params, ppaths, txtpcache, rebuilder):
        self.params = params
        self.ppaths = ppaths
        self.spaths = wgamesync.SilencePaths()
        self.txtpcache = txtpcache
        self.rebuilder = rebuilder
        self.info = wtxtp_info.TxtpInfo(wemnames=txtpcache.wemnames)  # node info to add in output as comment

        # config during printing
        self._selected = None       # current selected random in sub-txtp
        self.sparams = None         # current silence combo in sub-txtp

        return

    # start of txtp generation
    def begin(self, node, root_config, nname=None, ntid=None, ntidsub=None):
        # tree
        self._root = wtxtp_tree.TxtpNode(None, root_config)
        self._current = self._root

        # for info
        self._node = node
        self._nname = nname
        self._ntid = ntid
        self._ntidsub = ntidsub
        self._basepath = node.get_root().get_path()
        if not self._ntid:
            self._ntid = node.find1(type='sid')
        
        return

    #--------------------------------------------------------------------------

    def _get_name(self, printer, is_new=True):
        node = self._node #named based on default node, usually an event
        if self._nname:
            attrs = self._nname.get_attrs()
        elif self._ntid:
            attrs = self._ntid.get_attrs()
        else:
            attrs = {}

        hashname = attrs.get('hashname')
        guidname = attrs.get('guidname')

        is_stinger = self._ntidsub is not None

        #todo cache info
        if   hashname:
            name = hashname
        elif guidname:
            name = guidname
        else:
            #get usable name
            nroot = node.get_root()
            bankname = os.path.basename(nroot.get_filename()) #[:-4] #
            bankname = os.path.splitext(bankname)[0]

            name = None
            if bankname.isnumeric(): #try using hashname from bankname
                nbnk = nroot.find1(name='BankHeader')
                nbid = nbnk.find(name='dwSoundBankID')
                battrs = nbid.get_attrs()

                hashname = battrs.get('hashname')
                if hashname:
                    name = hashname
                #maybe could add language name?

            if not name:
                name = bankname

            if is_stinger:
                info = "{stinger=%s~%s}" % (self._ntid.value(), self._ntidsub.value())
                is_stinger = False
            else:
                attrs_node = node.get_attrs()
                index = attrs_node.get('index')
                if index is None: #shouldn't happen
                    info = self._ntid.value() #?
                else:
                    info = "%04u" % (int(index))


            if self.txtpcache.unused_mark:
                info += '~unused'
            if self.txtpcache.transition_mark:
                info += '~transition'

            classname = node.get_name()
            shortname = self.CLASSNAME_SHORTNAMES.get(classname)
            if shortname:
                name = "%s-%s-%s" % (name, info, shortname)
            else:
                name = "%s-%s" % (name, info)

            if self.txtpcache.x_nameid and self._ntid and self._ntid.value():
                name += "-%s" % (self._ntid.value())

        # for stingers, where the same id/name can trigger different segments
        if is_stinger:
            name += "-{stinger=~%s}" % (self._ntidsub.value())

        name += self.info.get_gsnames()

        if printer.has_silences():
            if self.txtpcache.silence:
                name += " {s-}" #"silence all"
            else:
                name += " {s}"
        name += self._get_sparams()

        name += self.info.get_wemnames()

        if printer.has_random_steps() or printer.is_selection():
            selection = printer.get_selected_main()
            if selection:
                name += " {r%s}" % (selection)
            else:
                name += " {r}"
        #if printer.has_random_continuous():
        #    name += " {rc}"
        if printer.has_externals():
            name += " {e}"
        if printer.has_multiloops():
            name += " {m}"
        if printer.has_internals() and self.txtpcache.bnkmark:
            name += " {b}"
        if printer.get_lang_name():
            name += " {l=%s}" % (printer.get_lang_name())
        if printer.has_unsupported():
            name += " {!}"
        if not is_new: #dupe
            #if is_not_exact_dupe:
            #    name += " {D}"
            name += " {d}"
        #if printer.has_others():
        #    name += " {o}"
        #if printer.has_self_loops():
        #    name += " {selfloop}"
        if printer.has_debug():
            name += " {debug}"

        #name += ".txtp"

        return name


    def _get_sparams(self):
        info = ''
        if not self.sparams:
            return info

        info += '='
        for group, value, group_name, value_name in self.sparams.items():
            gn = group_name or group
            vn = value_name or value
            if value == 0:
                vn = '-'
            info += "(%s=%s)" % (gn, vn)

        return info

    def _get_shortname(self):
        node = self._node #named based on default node, usually an event

        nroot = node.get_root()
        bankname = os.path.basename(nroot.get_filename()) #[:-4] #
        bankname = os.path.splitext(bankname)[0]

        name = "%s-%05i" % (bankname, self.txtpcache.names)

        return name

    def _get_info(self, name, longname):

        # base info
        info  = '\n\n'
        info += '# AUTOGENERATED WITH WWISER %s\n' % (wversion.WWISER_VERSION)
        info += '#\n'
        info += '# %s\n' % (name)
        if longname:
            info += '# * full name: %s\n' % (longname)

        #bank info
        banks = self.info.get_banks()
        #info += '#\n'
        #info += '# Banks:\n'
        for bank in banks:
            info += '# - %s\n' % (bank)

        # config info
        if self.txtpcache.volume_master:
            type = ''
            if self.txtpcache.volume_db:
                type = 'dB'
            info += '# ~ master volume %s%s\n' % (self.txtpcache.volume_master, type)

        if self._selected:
            extra = ''
            if self.txtpcache.random_force:
                extra = ' (forced)'
            info += '# ~ selected group=%s%s\n' % (self._selected, extra)
        info += '#\n'

        # tree info
        lines = self.info.get_lines()
        info += ''.join(lines)


        return info

    #--------------------------------------------------------------------------

    def write(self):
        printer = wtxtp_tree.TxtpPrinter(self, self._root)
        printer.prepare() #simplify tree

        # may have files but all silent
        if not printer.has_sounds():
            return

        # make one txtp per random/selectable group
        if self.txtpcache.random_all and printer.get_selectable_count():
            count = printer.get_selectable_count()
            # make one .txtp per random
            for i in range(1, count + 1):
                self._selected = i
                printer.set_selected_main(i)
                self._write_txtp(printer)

        else:
            # make main .txtp
            self._write_txtp(printer)

    def _write_txtp(self, printer):
        # handle sub-txtp per silence combo
        if self.spaths.empty:
            # without variables
            self._write_txtp_internal(printer)

        else:
            # per combo
            combos = self.spaths.combos()
            for combo in combos:
                self.sparams = combo
                self._write_txtp_internal(printer)

            self.sparams = None

            # generate a base .txtp with all songs in some cases
            # - multiple states used like a switch, base playing everything = bad (MGR, Bayo2)
            # - singe state used for on/off a single layer, base playing everything = good (AChain)
            if len(combos) == 1:
                self._write_txtp_internal(printer)

    def _write_txtp_internal(self, printer):
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

        # check hash
        is_new = self.txtpcache.register_txtp(texthash, printer)
        name = self._get_name(printer, is_new)
        if not is_new and not self.txtpcache.dupes:
            logging.debug("txtp: ignore '%s' (repeat of %s)", name, texthash)
            return False

        # same name but different txtp, rarely happens when banks repeat events ids that are actually different
        if not self.txtpcache.register_name(name):
            logging.debug("txtp: renaming to '%s'", name)
            name += '#%03i' % (self.txtpcache.names)

        for rpl in ['*','?',':','<','>','|']: #'\\','/'
            name = name.replace(rpl, "_")

        longname = None
        if self.txtpcache.tagsm3u:
            longname = name
            shortname = self._get_shortname() #todo should probably store after trimming
            name = shortname

            shortname += ".txtp"
            self.txtpcache._tag_names[shortname] = longname

        name += ".txtp"
        logging.debug("txtp: saving '%s' (%s)", name, texthash)

        outdir = self.txtpcache.outdir
        if outdir:
            outdir = os.path.join(self._basepath, outdir)
            os.makedirs(outdir, exist_ok=True)

        outname = outdir + name

        info = self._get_info(name, longname)

        # some variable combos or multi .wem names get too wordy
        if  self.txtpcache.is_windows:
            fullpath = self.txtpcache.basedir + '/' + outname
            if len(fullpath) > WINDOWS_MAX_PATH:
                maxlen = WINDOWS_MAX_PATH - len(self.txtpcache.basedir) - 10
                outname = "%s~%04i%s" % (outname[0:maxlen], self.txtpcache.created, '.txtp')
                self.txtpcache.trims += 1
                logging.debug("txtp: trimmed '%s'" % (outname)) #gets kinda noisy

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
