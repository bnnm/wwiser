

class _GraphPoint(object):
    def __init__(self, npoint):
        self.time = npoint.find(name='From').value() #time from (relative to music track)
        self.value = npoint.find(name='To').value() #current altered value
        self.interp = npoint.find(name='Interp').value() #easing function between points


class AkClipAutomation(object):
    def __init__(self, nclipam):
        self.index = None
        self.type = None
        self.points = []

        self._build(nclipam)

    def _build(self, nclipam):
        # clips have associated 'automations', that define graph points (making envelopes) to alter sound
        self.index = nclipam.find(name='uClipIndex').value() # which clip is affected (index N in clip list)
        self.type = nclipam.find(name='eAutoType').value() # type of alteration

        # types:
        # - fade-out: alters volume from A to B (in dB, so 0.0=100%, -96=0%)
        # - fade-in: same but in reverse
        # - LPF/HPF: low/high pass filter
        # - volume: similar but allows more points

        npoints = nclipam.finds(name='AkRTPCGraphPoint')
        for npoint in npoints:
            p = _GraphPoint(npoint) 
            self.points.append(p)
            # each point is discrete yet connected to next point via easing function
            # ex. point1: from=0.0, to=0.0, interp=sine
            #     point2: from=1.0, to=1.0, interp=constant
            # with both you have a fade in from 0.0..1.0, changing volume from silence to full in a sine curve

class AkClipAutomationList(object):
    def __init__(self, node):
        self.cas = {} #may have N clips per track
        self._build(node)

    def _build(self, node):
        # parse clip modifiers
        nclipams = node.finds(name='AkClipAutomation')
        for nclipam in nclipams:
            ca = AkClipAutomation(nclipam)

            if not ca.index in self.cas:
                self.cas[ca.index] = []
            self.cas[ca.index].append(ca)

    def get(self, track_index):
        return self.cas.get(track_index)
