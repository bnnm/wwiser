from .wrebuilder_base import CAkNode

# TRANSITION RULES
#
# When a musicswitch or musicranseq changes between objects, wwise can set config
# to tweaks how the audio transitions. Mostly "post-exit" and "pre-entry" info
# (play overlapped audio) and a optional transition object


class AkFade(CAkNode):
    def __init__(self, node):
        self.time = 0
        self.curve = None
        self.offset = 0

        self._build(node)

    def _build(self, node):
        self.time = node.find1(name='transitionTime').value()
        self.curve = node.find1(name='eFadeCurve').value()
        self.offset = node.find1(name='iFadeOffset').value()


class AkMusicTransSrcRule(CAkNode):
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


class AkMusicTransDstRule(CAkNode):
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

        # varies with version
        #uMarkerID
        #uCueFilterHash
        ncue = node.find(name='uCueFilterHash')
        if ncue:
            self.cue = ncue.value()
        nmrk = node.find(name='uMarkerID')
        if nmrk:
            self.cue = nmrk.value()
        pass
        #ty="tid" na="uJumpToID" va="0"/>
        #ty="u16" na="eEntryType" va="0" vf="0x00 [EntryMarker]"/>
        #ty="u8" na="bPlayPreEntry" va="255" vf="0xFF"/>
        #ty="u8" na="bDestMatchSourceCueName" va="0" vf="0x00"/>

class AkMusicTransitionObject(CAkNode):
    def __init__(self, nrtrn):
        self.sid = None
        self.fin = None
        self.fout = None
        self.pre = False
        self.post = False

        self._build(nrtrn)

    def _build(self, node):
        self.sid = node.find1(name='segmentID').value()

        nfin = node.find1(name='fadeInParams')
        self.fin = AkFade(nfin)
        nfout = node.find1(name='fadeOutParams')
        self.fin = AkFade(nfout)

        self.pre  = node.find1(name='bPlayPreEntry').value() != 0
        self.post = node.find1(name='bPlayPostExit').value() != 0

#TODO old versions check

class AkTransitionRule(CAkNode):
    def __init__(self, node):
        self.src_id = None
        self.dst_id = None
        self.rsrcs = []
        self.rdsts = []
        self.rtrn = None

        self._build(node)

    def _build(self, node):
        self.src = node.find1(name='srcID').value()
        self.dst = node.find1(name='dstID').value()

        nrsrcs = node.finds(name='AkMusicTransSrcRule')
        for nrsrc in nrsrcs:
            rsrc = AkMusicTransSrcRule(nrsrc)
            self.rdsts.append(rsrc)

        nrdsts = node.finds(name='AkMusicTransDstRule')
        for nrdst in nrdsts:
            rdst = AkMusicTransDstRule(nrdst)
            self.rdsts.append(rdst)

        nrtrn = node.find(name='AkMusicTransitionObject')
        if nrtrn:
            self.rtrn = AkMusicTransitionObject(nrtrn)


class AkTransitionRules(CAkNode):
    def __init__(self, node):
        self.rules = []

        self._build(node)

    def _build(self, node):
        nrules = node.finds(name='AkMusicTransitionRule')
        for nrule in nrules:
            rule = AkTransitionRule(nrule)
            self.rules.append(rule)

    def get_rule(self, src_id, dst_id):
        #TODO detect -1/0 too
        #for ...
        return None
