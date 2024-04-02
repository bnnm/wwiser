import logging, os

# use a bit less than 255 so files can be moved around dirs
# long paths can be enabled on Windows + python but detection+support is messy...
# (if not trimmed python may give an error on open W, even if individual path elems are less than 255)
WINDOWS_MAX_PATH = 240

# use a bit less than 255 for "base" filenames, too
# (max filename length on Linux is 255, even if dirs + name can be more than that
MAX_FILENAME_LENGTH = 240

_CLASSNAME_SHORTNAMES = {
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
}

class TxtpNamer(object):
    # info


    def __init__(self, txtp):
        self.txtp = txtp
        self.node = None
        self.ntid = None
        self.ncaller = None
        self.bstinger = None
        self.btransition = None


    def clean_name(self, name):
        txtp = self.txtp

        if not txtp.txtpcache.stats.register_namebase(name):
            logging.debug("txtp: renaming to '%s'", name)
            name += '#dupe#%03i' % (txtp.txtpcache.stats.current_name_count())

        # shouldn't happen but just in case
        for rpl in ['*','?',':','<','>','|']: #'\\','/'
            name = name.replace(rpl, "_")

        # rename txtp (before saving to tags)
        name = txtp.txtpcache.renamer.apply_renames(name)

        # change longname into shortname depending on config
        longname = None
        tags = txtp.txtpcache.tags
        if tags and tags.shortevent:
            longname = name
            if not tags.limit:
                shortname = self.get_shortname() # should store after trimming?
            else:
                if len(longname) > tags.limit:
                    cutname = longname[0:tags.limit] 
                    shortname = "%s~%04i" % (cutname, txtp.txtpcache.stats.created)
                else:
                    shortname = longname
            name = shortname

            shortname += ".txtp"
            tags.add_tag_names(shortname, longname)

        name += ".txtp"

        return name

    def get_outname(self, name, outdir):
        txtp = self.txtp


        # enforce max filename (few OSes support more than that)
        if len(name) > MAX_FILENAME_LENGTH:
            #if not longname:
            #    longname = name
            name = "%s~%04i%s" % (name[0:MAX_FILENAME_LENGTH], txtp.txtpcache.stats.created, '.txtp')
            txtp.txtpcache.stats.trims += 1
            logging.debug("txtp: trimmed name '%s'", name)

        outname = os.path.join(outdir, name)

        # final name after path can be a bit too big
        if  txtp.txtpcache.is_windows:
            # in GUI may outname may be a full path already
            if ':' in outname:
                fullpath = outname
            else:
                fullpath = txtp.txtpcache.basedir + '/' + outname

            if len(fullpath) > WINDOWS_MAX_PATH:
                maxlen = WINDOWS_MAX_PATH - len(txtp.txtpcache.basedir) - 10
                outname = "%s~%04i%s" % (outname[0:maxlen], txtp.txtpcache.stats.created, '.txtp')
                txtp.txtpcache.stats.trims += 1
                logging.debug("txtp: trimmed path '%s'", outname)

        return outname

    # gets final txtp name, full version (without .txtp)
    def get_longname(self, printer):
        txtp = self.txtp
        node = self.node #named based on default node, usually an event

        ntid = self.ntid
        

        if ntid:
            attrs = ntid.get_attrs()
        else:
            attrs = {}


        hashname = attrs.get('hashname')
        guidname = attrs.get('guidname')

        # adds extra info in some cases
        extra_name = False
        if not hashname and self.ncaller:
            hashname = self.ncaller.get_attrs().get('hashname')

        if not hashname and not guidname:
            extra_name = True


        is_stinger = self.bstinger is not None
        is_transition = self.btransition is not None
        is_unused = txtp.txtpcache.stats.unused_mark

        # name examples:
        # - play_music
        # - play_music
        # - play_music~{stinger=trigger001~123456789} (bgm=b001)
        # - play_music~transition
        # - bgm--event-{stinger=trigger001~123456789}
        # - bgm--event~unused-{stinger=trigger001~123456789}


        # get base name
        if   hashname:
            name = hashname
        elif guidname:
            name = guidname
        else:
            name = None

            nroot = node.get_root()
            bankname = os.path.basename(nroot.get_filename()) #[:-4] #
            bankname = os.path.splitext(bankname)[0]

            # use bank's hashname if available
            nbnk = nroot.find1(name='BankHeader')
            nbid = nbnk.find(name='dwSoundBankID')
            battrs = nbid.get_attrs()
            hashname = battrs.get('hashname')
            if hashname:
                name = hashname

            # otherwise use bank's name
            if not name:
                name = bankname


        # add extra info to the name
        if extra_name:
            #include base node's tid
            attrs_node = node.get_attrs()
            index = attrs_node.get('index')
            if index is None: #shouldn't happen...
                info = ntid.value() #?
            else:
                info = "%04u" % (int(index))

            # usually only regular objects can be like this (here so it shows like -xxxx~unused-musicsegment)
            if is_unused:
                info += '~unused'

            classname = node.get_name()
            shortname = _CLASSNAME_SHORTNAMES.get(classname)
            if shortname:
                name = "%s-%s-%s" % (name, info, shortname)
            else:
                name = "%s-%s" % (name, info)

            if txtp.txtpcache.x_nameid and ntid and ntid.value():
                name += "-%s" % (ntid.value())

        if is_transition:
            attrs_node = node.get_attrs()
            index = attrs_node.get('index') #segment index
            if index is None: #shouldn't happen...
                info = self.btransition.tid #segment id, looks a bit messier
            else:
                info = "%04u" % (int(index))

            # in theory same transition segment could be in different banks but 
            # since we have the event name should be enough to tell them apart
            name += '~{transition-%s}' % (info)

        # a trigger (hashname) can call different segments, so we need both
        if is_stinger:
            attrs_node = node.get_attrs()
            index = attrs_node.get('index') #segment index
            if index is None: #shouldn't happen...
                info = self.bstinger.tid #segment id, looks a bit messier
            else:
                info = "%04u" % (int(index))

            ntrigger = self.bstinger.ntrigger
            trigname = ntrigger.get_attrs().get('hashname')
            if not trigname:
                trigname = ntrigger.value()

            name += "~{stinger-%s}=%s" % (info, trigname)

        # params
        name += txtp.info.get_gsnames()

        # extra flags
        # only show {s} if there are multiple crossfading sounds, or if user has ser manual variables
        sc = self._get_scparams()
        gv = self._get_gamevars(printer)
        if printer.is_crossfading_multiple() or sc or gv:
            if txtp.txtpcache.x_silence_all:
                name += " {s-}"
            else:
                name += " {s}"
        name += sc
        name += gv


        name += txtp.info.get_wemnames()

        if printer.has_random_steps:
            if printer.is_random_select:
                name += " {r%s}" % (txtp.selected)
            else:
                name += " {r}"
        #if printer.has_random_continuous:
        #    name += " {rc}"
        if printer.has_multiloops:
            if printer.is_multi_select:
                name += " {m%s}" % (txtp.selected)
            else:
                name += " {m}"
        if printer.is_force_select:
            name += " {f%s}" % (txtp.selected)

        if printer.lang_name:
            name += " {l=%s}" % (printer.lang_name)
        if printer.has_internals and txtp.txtpcache.bnkmark:
            name += " {b}"

        if printer.has_externals:
            if txtp.external_name:
                name += " {e=%s}" % (txtp.external_name)
            else:
                # could try to set list of used "cookie" IDs ({e=123456}) to help users, but probably useless
                # since txtp name has tons of numbers already and may be confused at a glance with those,
                # plus externals aren't that used.
                name += " {e}"

        if printer.has_unsupported or printer.has_many_sounds():
            name += " {!}"

        if printer.has_debug:
            name += " {debug}"

        #name += ".txtp"

        return name

    def get_dupename(self, name):
        #if is_not_exact_dupe:
        #    name += " {D}"
        name += " {d}"

        return name

    def _get_scparams(self):
        txtp = self.txtp

        scnames = txtp.info.get_scnames()
        if not scnames:
            if txtp.scparams_make_default:
                return '=-'
            return scnames

        info = '='
        info += txtp.info.get_scnames()

        return info

    def _get_gamevars(self, printer):
        txtp = self.txtp
        info = ''

        gvnames = txtp.info.get_gvnames()
        if not gvnames:
            return info

        # show {s}={vars} is user has set vars (even if there aren't multiple corssfading variables)
        if printer.has_silences: #printer.is_crossfading_multiple():
            info += '='
        else:
            info += ' '
        info += txtp.info.get_gvnames()

        return info

    # gets final txtp name, short version (without .txtp)
    def get_shortname(self):
        txtp = self.txtp
        node = self.node #named based on default node, usually an event

        nroot = node.get_root()
        bankname = os.path.basename(nroot.get_filename()) #[:-4] #
        bankname = os.path.splitext(bankname)[0]

        name = "%s-%05i" % (bankname, txtp.txtpcache.stats.current_name_count())

        return name
