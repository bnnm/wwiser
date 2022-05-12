# TRANSITION RULES
#
# When a musicswitch or musicranseq changes between objects, wwise can set config
# to tweaks how the audio transitions. Mostly "post-exit" and "pre-entry" info
# (play overlapped audio) and a optional transition object


class AkFade(object):
    def __init__(self, node):
        self.time = 0
        self.curve = None
        self.offset = 0

        self._build(node)

    def _build(self, node):
        self.time = node.find1(name='transitionTime').value()
        self.curve = node.find1(name='eFadeCurve').value()
        self.offset = node.find1(name='iFadeOffset').value()


class AkMusicTransSrcRule(object):
    def __init__(self, node):
        self.fade = None
        self.type = None
        self.post = False
        self.link_id = None
        self.link_cue = None
        self._build(node)

    def _build(self, node):
        self.fade = AkFade(node)
        self.type = node.find1(name='eSyncType').value()
        self.post = node.find1(name='bPlayPostExit').value() != 0

        ncue = node.find(name='uCueFilterHash')
        if ncue:
            self.cue = ncue.value()


class AkMusicTransDstRule(object):
    def __init__(self, node):
        self.fade = None
        self.type = None
        self.post = False
        self.link_id = None
        self.link_cue = None
        self._build(node)

    def _build(self, node):
        self.fade = AkFade(node)
        self.type = node.find1(name='eEntryType').value()
        self.post = node.find1(name='bPlayPreEntry').value() != 0

        # varies with version
        #uMarkerID
        #uCueFilterHash
        ncue = node.find(name='uCueFilterHash')
        if ncue:
            self.link_cue = ncue.value()
        nmrk = node.find(name='uMarkerID')
        if nmrk:
            self.link_id = nmrk.value()

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

#TODO old versions check

class AkTransitionRule(object):
    def __init__(self, node):
        self.src_id = None
        self.dst_id = None
        self.rsrcs = []
        self.rdsts = []
        self.rtrn = None

        self._build(node)

    def _build(self, node):
        # id=object, -1=any, 0=nothing
        self.src_id = node.find1(name='srcID').value()
        self.dst_id = node.find1(name='dstID').value()
        
        nrsrcs = node.finds(name='AkMusicTransSrcRule')
        for nrsrc in nrsrcs:
            rsrc = AkMusicTransSrcRule(nrsrc)
            self.rdsts.append(rsrc)

        nrdsts = node.finds(name='AkMusicTransDstRule')
        for nrdst in nrdsts:
            rdst = AkMusicTransDstRule(nrdst)
            self.rdsts.append(rdst)

        # older versions use bIsTransObjectEnabled to signal use, but segmentID is 0 if false anyway
        nrtrn = node.find(name='AkMusicTransitionObject')
        if nrtrn:
            self.rtrn = AkMusicTransitionObject(nrtrn)


class AkTransitionRules(object):
    def __init__(self, node):
        self._rules = []
        self.ntrn = []

        self._build(node)

    def _build(self, node):
        nrules = node.finds(name='AkMusicTransitionRule')
        for nrule in nrules:
            rule = AkTransitionRule(nrule)
            self._rules.append(rule)
            if rule.rtrn and rule.rtrn.ntid:
                self.ntrn.append(rule.rtrn.ntid)

    def get_rule(self, src_id, dst_id):
        #TODO detect -1/0 too
        #for ...
        return None
