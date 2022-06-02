# TRANSITION RULES
#
# When a musicswitch or musicranseq changes between objects, wwise can set config
# to tweaks how the audio transitions. Mostly "post-exit" and "pre-entry" info
# (play overlapped audio) and a optional transition object


class AkFade(object):
    def __init__(self, node):
        self.time = 0
        self.offset = 0
        self.curve = None

        self._build(node)

    def _build(self, node):
        self.time = node.find1(name='transitionTime').value()
        self.offset = node.find1(name='iFadeOffset').value()
        self.curve = node.find1(name='eFadeCurve').value()


class AkMusicTransSrcRule(object):
    def __init__(self, node):
        self.fade = None
        self.type = None
        self.play = False #post exit
        self._build(node)

    def _build(self, node):
        self.fade = AkFade(node)
        self.type = node.find1(name='eSyncType').value()
        self.play = node.find1(name='bPlayPostExit').value() != 0

        #ncue = node.find(name='uCueFilterHash')
        #if ncue:
        #    self.cue = ncue.value()


class AkMusicTransDstRule(object):
    def __init__(self, node):
        self.fade = None
        self.type = None
        self.play = False #pre extry
        self._build(node)

    def _build(self, node):
        self.fade = AkFade(node)
        self.type = node.find1(name='eEntryType').value()
        self.play = node.find1(name='bPlayPreEntry').value() != 0

        # varies with version
        #uMarkerID
        #uCueFilterHash
        #ncue = node.find(name='uCueFilterHash')
        #if ncue:
        #    self.link_cue = ncue.value()
        #nmrk = node.find(name='uMarkerID')
        #if nmrk:
        #    self.link_id = nmrk.value()

        #uJumpToID
        #eJumpToType
        #bDestMatchSourceCueName

class AkMusicTransitionObject(object):
    def __init__(self, node):
        self.ntid = None
        self.tid = None
        self.fin = None
        self.fout = None
        self.pre = False
        self.post = False

        self._build(node)

    def _build(self, node):
        self.ntid = node.find1(name='segmentID') 
        self.tid = self.ntid.value()

        nfin = node.find1(name='fadeInParams')
        self.fin = AkFade(nfin)
        nfout = node.find1(name='fadeOutParams')
        self.fin = AkFade(nfout)

        self.pre  = node.find1(name='bPlayPreEntry').value() != 0
        self.post = node.find1(name='bPlayPostExit').value() != 0


class AkTransitionRule(object):
    def __init__(self, node):
        self.src_ids = []
        self.dst_ids = []
        self.rsrc = None
        self.rdst = None
        self.rtrn = None

        self._build(node)

    def _build(self, node):
        # id=object, -1=any, 0=nothing

        # v088+ allows N but not sure how it's used, editor only sets one by one (seen in Detroit)
        nsrc_ids = node.finds(name='srcID')
        for nsrc_id in nsrc_ids:
            self.src_ids.append(nsrc_id.value())

        ndst_ids = node.finds(name='dstID')
        for ndst_id in ndst_ids:
            self.dst_ids.append(ndst_id.value())

        nrsrc = node.find(name='AkMusicTransSrcRule')
        self.rsrc = AkMusicTransSrcRule(nrsrc)

        nrdst = node.find(name='AkMusicTransDstRule')
        self.rdst = AkMusicTransDstRule(nrdst)

        # older versions use bIsTransObjectEnabled to signal use, but segmentID is 0 if false anyway
        nrtrn = node.find(name='AkMusicTransitionObject')
        if nrtrn:
            self.rtrn = AkMusicTransitionObject(nrtrn)


class AkTransitionRules(object):
    def __init__(self, node):
        self._rules = []
        self.ntrns = []

        self._build(node)

    def _build(self, node):
        nrules = node.finds(name='AkMusicTransitionRule')
        for nrule in nrules:
            rule = AkTransitionRule(nrule)
            self._rules.append(rule)
            if rule.rtrn and rule.rtrn.tid: #segment 0 = useless
                self.ntrns.append(rule.rtrn)

    def get_rule(self, src_id, dst_id):
        #TODO implement (detect -1/0 too)
        #for ...
        return None

    def get_rules(self):
        return self._rules
