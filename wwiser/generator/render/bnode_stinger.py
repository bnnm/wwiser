# STINGERS/TRIGGERS
#
# Some objects can contain a reference to another object, that plays when the game posts
# a "trigger" (via API or calling a CAkTrigger from an event)

class CAkStinger(object):
    def __init__(self, node):
        self.ntrigger = None
        self.ntid = None
        self.tid = None
        self._build(node)

    def _build(self, node):
        self.ntrigger = node.find1(name='TriggerID') #idExt called from trigger action
        self.ntid = node.find1(name='SegmentID') #musicsegment to play (may be 0)
        if self.ntid:
            self.tid = self.ntid.value()

class CAkStingerList(object):
    def __init__(self, node):
        self.stingers = []
        self._build(node)

    def _build(self, node):
        nstingers = node.finds(name='CAkStinger')
        if not nstingers:
            return

        for nstinger in nstingers:
            stinger = CAkStinger(nstinger)
            if stinger.tid:
                self.stingers.append(stinger)
