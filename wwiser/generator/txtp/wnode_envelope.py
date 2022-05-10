
# DmC (65): old
# MGR (72): new (probably v70 too)
_ENVELOPE_NEW_VERSION = 70

_TXTP_INTERPOLATIONS = {
    0:'L', #Log3
    1:'Q', #Sine
    2:'L', #Log1
    3:'H', #InvSCurve
    4:'T', #Linear
    5:'H', #SCurve
    6:'E', #Exp1
    7:'Q', #SineRecip
    8:'E', #Exp3
    9:'T', #Constant
}

class NodeEnvelope(object):
    def __init__(self, am, p1, p2, version=0, base_time=0):
        self.usable = False
        self.is_volume = False
        self.vol1 = None
        self.vol2 = None
        self.shape = None
        self.time1 = None
        self.time2 = None
        if not am or not p1 or not p2:
            return

        # LFE work differently        
        if version < _ENVELOPE_NEW_VERSION:
            ignorable_types = [1] #LFE
        else:
            ignorable_types = [1,2] #LFE,HFE
        if am.type in ignorable_types:
            return
        self.is_volume = True

        self.vol1 = p1.value
        self.vol2 = p2.value

        # constant is an special value that should ignore p2
        if (p1.interp == 9):
            self.vol2 = self.vol1

        # normalize volumes
        if version < _ENVELOPE_NEW_VERSION:
            # convert -96.0 .. 0.0 .. 96.0 dB to volume
            self.vol1 = pow(10.0, self.vol1 / 20.0)
            self.vol2 = pow(10.0, self.vol2 / 20.0)
        else:
            if am.type == 0: # volume
                # convert -1.0 .. 0.0 .. 1.0 to 0.0 .. 1.0 .. 2.0
                self.vol1 += 1.0
                self.vol2 += 1.0
            else: # fades
                # standard 0.0 .. 1.0
                pass

        # some points are just used to delay with no volume change
        # note that constant different volumes exists (ex. -0.24 .. -0.24 on doomy ternal)
        if self.vol1 == 1.0 and self.vol2 == 1.0:
            return

        #todo approximate curves, improve
        self.shape = _TXTP_INTERPOLATIONS.get(p1.interp, '{')

        self.time1 = p1.time + base_time
        self.time2 = p2.time - p1.time

        self.usable = True

# transform wwise automations to txtp envelopes
# wwise defines points (A,B,C) and autocalcs combos like (A,B),(B,C).
# for txtp we need to make combos
# ch(type)(position)(time-start)+(time-length)
# ch^(volume-start)~(volume-end)=(shape)@(time-pre)~(time-start)+(time-length)~(time-last)
def build_txtp_envelopes(automations, version, base_time):
    envelopes = []

    #todo apply delays

    for am in automations:
        max = len(am.points)
        for i in range(0, max):
            if (i + 1 >= max):
                continue

            p1 = am.points[i]
            p2 = am.points[i+1]
            envelope = NodeEnvelope(am, p1, p2, version, base_time)
            if not envelope.usable or not envelope.is_volume:
                continue

            envelopes.append(envelope)
    return envelopes
