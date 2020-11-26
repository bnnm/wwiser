import logging, math, os
from . import wgamesync, wtxtp_tree, wversion


DEFAULT_OUTDIR = 'txtp/'
DEFAULT_WEMDIR = 'wem/'

#use a bit less than 255 so files can be moved around dirs
#long paths can be enabled on Windows but detection+support is messy...
WINDOWS_MAX_PATH = 235


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

        self.x_nocrossfade = True
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
        self.is_windows = os.name == 'nt'
        self.basedir = os.getcwd()

        self._txtp_hashes = {}
        self._name_hashes = {}
        self._banks = {}

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

#******************************************************************************

class Txtp(object):
    def __init__(self, params, ppaths, txtpcache, rebuilder):
        self.params = params
        self.ppaths = ppaths
        self._txtpcache = txtpcache
        self._rebuilder = rebuilder

        self._node = None
        self._info = []

        self._object_names = {
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

        return

    def begin(self, node, root_config, nname=None, ntid=None, ntidsub=None):
        #tree
        self._root = wtxtp_tree.TxtpNode(None, root_config)
        self._current = self._root

        self._node = node           # base node
        self._nname = nname
        self._ntid = ntid
        self._ntidsub = ntidsub
        self._depth = 0             # info for padding

        if not self._ntid:
            self._ntid = node.find1(type='sid')

        self._basename = ''         # final name
        self._ninfo = []            # node info to add in output as comment
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
                    

            if self._txtpcache.unused_mark:
                info += '~unused'
            if self._txtpcache.transition_mark:
                info += '~transition'

            classname = node.get_name()
            subname = self._object_names.get(classname)
            if subname:
                name = "%s-%s-%s" % (name, info, subname)
            else:
                name = "%s-%s" % (name, info)

            if self._txtpcache.x_nameid and self._ntid and self._ntid.value():
                name += "-%s" % (self._ntid.value())

        # for stingers, where the same id/name can trigger different segments
        if is_stinger:
            name += "-{stinger=~%s}" % (self._ntidsub.value())

        name += self._basename
        if printer.has_randoms():
            name += " {r}"
        if printer.has_externals():
            name += " {e}"
        if printer.has_multiloops():
            name += " {m}"
        if printer.has_silences():
            name += " {s}"
        if printer.has_internals() and self._txtpcache.bnkmark:
            name += " {b}"
        if printer.get_lang_name():
            name += " {l=%s}" % (printer.get_lang_name())
        #if printer.has_self_loops():
        #    name += " {selfloop}"
        if printer.has_unsupported():
            name += " {!}"
        if not is_new:
            name += " {d}"

        #name += ".txtp"

        return name

    def _get_info(self, name):
        lines = []

        banks = self._get_info_banks()
        is_multibank = len(banks) > 1

        for ninfo in self._ninfo:
            info = ninfo.generate(is_multibank)
            lines.append(info)

        info  = '\n\n'
        info += '# AUTOGENERATED WITH WWISER %s\n' % (wversion.WWISER_VERSION)
        info += '#\n'
        info += '# %s\n' % (name)
        for bank in banks:
            info += '# - %s\n' % (bank)

        if self._txtpcache.volume_master:
            type = ''
            if self._txtpcache.volume_db:
                type = 'dB'
            info += '# ~ master volume %s%s\n' % (self._txtpcache.volume_master, type)
        #if self._txtpcache.x_nocrossfade:
        #    info += '# ~ no crossfade\n'

        info += '#\n'
        info += ''.join(lines)
        return info

    def _get_info_banks(self):
        banks = []
        for ninfo in self._ninfo:
            node = ninfo.get_node()
            if node:
                bank = node.get_root().get_filename()
                if bank not in banks:
                    banks.append(bank)
        return banks

    def write(self):
        printer = wtxtp_tree.TxtpPrinter(self, self._root, self._txtpcache, self._rebuilder)
        text = printer.process()

        # may have files but all silent
        if not printer.has_sounds():
            return

        #some games have many GS combos that end up being the same (ex. Nier Automata, Bayonetta 2)
        texthash = hash(text)
        is_new = self._txtpcache.register_txtp(texthash, printer)
        name = self._get_name(printer, is_new)
        if not is_new and not self._txtpcache.dupes:
            logging.debug("txtp: ignore '%s' (repeat of %s)", name, texthash)
            return False

        #same name but different txtp, shouldn't happen (just in case, maybe when loading many banks?)
        if not self._txtpcache.register_name(name):
            logging.debug("txtp: renaming to '%s'", name)
            name += '#%03i' % (self._txtpcache.names)

        for rpl in ['*','?',':','<','>','|']: #'\\','/'
            name = name.replace(rpl, "_")
        name += ".txtp"
        logging.debug("txtp: saving '%s' (%s)", name, texthash)

        outdir = self._txtpcache.outdir
        if outdir:
            basepath = self._node.get_root().get_path()
            outdir = os.path.join(basepath, outdir)
            os.makedirs(outdir, exist_ok=True)

        outname = outdir + name

        info = self._get_info(name)

        # some variable combos or multi .wem names get too wordy
        if  self._txtpcache.is_windows:
            fullpath = self._txtpcache.basedir + '/' + outname
            if len(fullpath) > WINDOWS_MAX_PATH:
                maxlen = WINDOWS_MAX_PATH - len(self._txtpcache.basedir) - 10
                outname = "%s~%04i%s" % (outname[0:maxlen], self._txtpcache.created, '.txtp')
                self._txtpcache.trims += 1
                logging.debug("txtp: trimmed '%s'" % (outname)) #gets kinda noisy

        if self._txtpcache.x_notxtp:
            return

        with open(outname, 'w', encoding='utf-8') as outfile:
            outfile.write(text)
            outfile.write(info)
        return

    #--------------------------------------------------------------------------

    def group_random(self, elems, config):
        if not elems:
            return
        #self._basename += ' {r~%i}' % (len(elems))
        return self._group_add(config).random()

    def group_sequence(self, elems, config):
        if not elems:
            return
        #self._basename += ' {s~%i}' % (len(elems))
        return self._group_add(config).sequence()

    def group_layer(self, elems, config):
        if not elems:
            return
        #self._basename += ' {l~%i}' % (len(elems))
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
        #self._current = node
        return self._current

    #--------------------------------------------------------------------------

    def info_source(self, ntid, source):
        nfields = None
        if source:
            nfields = [source.nplugin]
    
        next = TxtpInfo(self._depth + 1, None, nfields, None, source=ntid)
        self._ninfo.append(next)

        if self._txtpcache.wemnames:
            attrs = ntid.get_attrs()
            wemname = attrs.get('guidname', attrs.get('path'))
            if wemname:
                basename = os.path.basename(wemname) #[:-4]
                basename = os.path.splitext(basename)[0]
                basename = basename.strip()
                finalname = "{%s}" % (basename)
                if finalname not in self._basename:
                    self._basename += ' ' + finalname

    def info_next(self, node, nfields, nattrs=None, nsid=None):
        self._depth += 1

        next = TxtpInfo(self._depth, node, nfields, nattrs, nsid=nsid)
        self._ninfo.append(next)

    def info_done(self):
        self._depth -= 1

    def info_gamesync(self, gtype, ngname, ngvalue):
        self.info_gamesyncs([(gtype, ngname, ngvalue)])

    def info_gamesyncs(self, gamesyncs):
        current = self._ninfo[-1]

        current.add_gamesyncs(gamesyncs)
        info = current.get_gamesync_text()

        self._basename += " " + info

#******************************************************************************

class TxtpInfo(object):
    OBJECT_NAMES = ['hashname', 'guidname', 'path', 'objpath']

    def __init__(self, depth, node, nfields, nattrs, nsid=None, source=None):
        self.depth = depth
        self.node = node
        self.nsid = nsid
        self.nfields = nfields
        self.nattrs = nattrs
        self.gamesync = '' #text
        self.source = source
        self._info = []

    def add_gamesyncs(self, gamesyncs):
        if self.gamesync:
            raise ValueError("multiple gamesyncs in same info node")

        info = ''
        for gtype, ngname, ngvalue in gamesyncs:

            name = ngname.get_attrs().get('hashname')
            if not name:
                name = ngname.value()
            value = ngvalue.get_attrs().get('hashname')
            if not value:
                value = ngvalue.value()
            if value == 0:
                value = '-'

            if   gtype == wgamesync.GamesyncParams.TYPE_STATE:
                type = "(%s=%s)" % (name, value) # states = more globals = "("
            elif gtype == wgamesync.GamesyncParams.TYPE_SWITCH:
                type = "[%s=%s]" % (name, value) # switches = more restrictive = "["
            else:
                raise ValueError("unknown gamesync type %i" % (gtype))

            info += type

        self.gamesync = info

    def get_gamesync_text(self):
        return self.gamesync

    def get_node(self):
        return self.node

    def generate(self, multibank=False):
        self.padding = ' ' * (self.depth * 2 + 1) #+1 for '# ' space after comment 

        self._generate_node(multibank)
        self._generate_gamesync()
        self._generate_source()
        self._generate_fields()

        self._info.append('#\n')
        return ''.join(self._info)

    def _generate_node(self, multibank):
        node = self.node
        if not node:
            return
        index = node.get_attr('index')

        nsid = self.nsid
        if not nsid:
            nsid = node.find1(type='sid')

        line = ''
        # base node
        line += node.get_name()
        if index is not None:
            line += '[%s]' % (index)
        if nsid:
            line += ' %i' % (nsid.value())

        if multibank:
            line += ' / %s' % (node.get_root().get_filename())

        self._info.append( '#%s%s\n' % (self.padding, line) )

        # node names
        if nsid:
            attrs = nsid.get_attrs() #base object > sid + names
        else:
            attrs = node.get_attrs() #regular node with names

        for key, val in attrs.items():
            if not key in self.OBJECT_NAMES:
                continue
            self._info.append( '#%s- %s: %s\n' % (self.padding, key, val) )

    def _generate_fields(self):
        if not self.nfields:
            return
        for nfield in self.nfields:
            if not nfield:
                continue
                #raise ValueError("empty field (old version?)")

            if isinstance(nfield, tuple):
                if   len(nfield) == 2:
                    nkey, nval = nfield
                    kattrs = nkey.get_attrs()
                    vattrs = nval.get_attrs()

                    kname = kattrs.get('name')
                    kvalue = kattrs.get('valuefmt', kattrs.get('hashname'))
                    if not kvalue:
                        kvalue = kattrs.get('value')

                    if not kvalue:
                        key = "%s" % (kname)
                    else:
                        key = "%s %s" % (kname, kvalue)

                    val = vattrs.get('valuefmt', vattrs.get('hashname'))
                    if not val:
                        val = vattrs.get('value')

                elif len(nfield) == 3:
                    nkey, nmin, nmax = nfield
                    kattrs = nkey.get_attrs()
                    minattrs = nmin.get_attrs()
                    maxattrs = nmax.get_attrs()
                    key = "%s %s" % (kattrs.get('name'), kattrs.get('valuefmt', kattrs.get('value')))
                    val = "(%s, %s)" % (minattrs.get('valuefmt', minattrs.get('value')), maxattrs.get('valuefmt', maxattrs.get('value')))

                else:
                    raise ValueError("bad tuple")
            else:
                attrs = nfield.get_attrs()
                key = attrs.get('name')
                val = attrs.get('valuefmt', attrs.get('hashname'))
                if not val:
                    val = attrs.get('value')

            self._info.append( '#%s* %s: %s\n' % (self.padding, key, val) )

    def _generate_gamesync(self):
        if not self.gamesync:
            return
        self._info.append( '#%s~ %s\n' % (self.padding, self.gamesync) )

    def _generate_source(self):
        ntid = self.source
        if not ntid:
            return

        attrs = ntid.get_attrs()
        names = set(['hashname', 'guidname', 'path', 'objpath'])

        name = 'Source'
        sid = ntid.value()

        self._info.append( '#%s%s %i\n' % (self.padding, name, sid) )
        for key, val in attrs.items():
            if not key in names:
                continue
            self._info.append( '#%s- %s: %s\n' % (self.padding, key, val) )
