import os

class TxtpNamer(object):
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


    def __init__(self, txtp):
        self.txtp = txtp

        self.node = None
        self.nname = None
        self.ntid = None
        self.ntidsub = None



    def get_fullname(self, printer, is_new=True):
        txtp = self.txtp
        node = self.node #named based on default node, usually an event

        nname = self.nname
        ntid = self.ntid
        ntidsub = self.ntidsub
        

        if nname:
            attrs = nname.get_attrs()
        elif ntid:
            attrs = ntid.get_attrs()
        else:
            attrs = {}


        hashname = attrs.get('hashname')
        guidname = attrs.get('guidname')

        is_stinger = ntidsub is not None

        #todo cache info
        if   hashname:
            name = hashname
        elif guidname:
            name = guidname
        else:
            #get usable name
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

            if is_stinger:
                info = "{stinger=%s~%s}" % (ntid.value(), ntidsub.value())
                is_stinger = False
            else:
                attrs_node = node.get_attrs()
                index = attrs_node.get('index')
                if index is None: #shouldn't happen
                    info = ntid.value() #?
                else:
                    info = "%04u" % (int(index))


            if txtp.txtpcache.unused_mark:
                info += '~unused'
            if txtp.txtpcache.transition_mark:
                info += '~transition'

            classname = node.get_name()
            shortname = self.CLASSNAME_SHORTNAMES.get(classname)
            if shortname:
                name = "%s-%s-%s" % (name, info, shortname)
            else:
                name = "%s-%s" % (name, info)

            if txtp.txtpcache.x_nameid and ntid and ntid.value():
                name += "-%s" % (ntid.value())

        # for stingers, where the same id/name can trigger different segments
        if is_stinger:
            name += "-{stinger=~%s}" % (ntidsub.value())

        name += txtp.info.get_gsnames()

        if printer.has_silences:
            if txtp.txtpcache.silence:
                name += " {s-}" #"silence all"
            else:
                name += " {s}"
        name += self._get_sparams()

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
                name += " {e}"

        if printer.has_unsupported:
            name += " {!}"
        if not is_new: #dupe
            #if is_not_exact_dupe:
            #    name += " {D}"
            name += " {d}"
        #if printer.has_others:
        #    name += " {o}"
        #if printer.has_self_loops:
        #    name += " {selfloop}"
        if printer.has_debug:
            name += " {debug}"

        #name += ".txtp"

        return name


    def _get_sparams(self):
        txtp = self.txtp

        info = ''
        if not txtp.sparams:
            return info

        info += '='
        for group, value, group_name, value_name in txtp.sparams.items():
            gn = group_name or group
            vn = value_name or value
            if value == 0:
                vn = '-'
            info += "(%s=%s)" % (gn, vn)

        return info

    def get_shortname(self):
        txtp = self.txtp
        node = self.node #named based on default node, usually an event

        nroot = node.get_root()
        bankname = os.path.basename(nroot.get_filename()) #[:-4] #
        bankname = os.path.splitext(bankname)[0]

        name = "%s-%05i" % (bankname, txtp.txtpcache.names)

        return name
