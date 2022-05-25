
# DmC (65): old volumes
# MGR (72): new volumes (probably v70 too)
_AUTOMATION_NEW_VOLUME_VERSION = 70
# 
_AUTOMATION_NEW_TYPE_VERSION = 112


# Wwise marks a type like "Exp1" when doing any fades, but due to how curves
# are programmed, fade-ins are standard and fade-outs must use the inverse curve.
# So fade-in Exp1 uses 'E' (lowered) while fade-out must be 'L' (raised).
# TXTP's curves (not documented) are more limited, so fades aren't 100% exact:
# - E: exponential (2.5)
# - L: logaritmic (2.5)
# - H: raised sine/cosine 
# - Q: quarter sine/cosine 
# - p: parabola
# - P: inverted parabola
# - T: triangular/linear
# - {}: alias of one of the above
# - (): alias of one of the above
#
# And Wwise's curves:                           
# - 0: Log3 (raised high)
# - 1: Sine (raised normal)
# - 2: Log1 (raised low, almost linear)
# - 3: InvSCurve (sharp S in the middle)
# - 4: Linear (simple)
# - 5: SCurve (shoft S in the middle)
# - 6: Exp1 (lowered low, almost linear)
# - 7: SineRecip (lowered mid)
# - 8: Exp3 (lowered low)
# - 9: Constant (fixed output)
#
# Where 'raised' = rises soon, and 'lowered' = rises later, roughly:
#       .....               ...
#     ..                   .
#    .                     .
#   .                     .
#   .                   .. 
#  .                ....

_TXTP_INTERPOLATIONS_FADEIN = {
    0:'L', #Log3
    1:'P', #Sine
    2:'P', #Log1
    3:'H', #InvSCurve
    4:'T', #Linear
    5:'Q', #SCurve
    6:'p', #Exp1
    7:'p', #SineRecip
    8:'E', #Exp3
    9:'T', #Constant
}

_TXTP_INTERPOLATIONS_FADEOUT = {
    0:'E', #Log3
    1:'p', #Sine
    2:'p', #Log1
    3:'Q', #InvSCurve
    4:'T', #Linear
    5:'H', #SCurve
    6:'P', #Exp1
    7:'P', #SineRecip
    8:'L', #Exp3
    9:'T', #Constant
}

class NodeEnvelope(object):
    def __init__(self, automation, p1, p2, version=0):
        self.usable = False
        self.is_volume = False
        self.vol1 = None
        self.vol2 = None
        self.shape = None
        self.time1 = None
        self.time2 = None
        if not automation or not p1 or not p2:
            return

        # ignore unusable effects
        if version < _AUTOMATION_NEW_TYPE_VERSION:
            ignorable_types = [1] #0=volume 1=LPF 2=fadein 3=fadeout
        else:
            ignorable_types = [1,2] #0=volume 1=LPF 2=HDF 3=fadein 4=fadeout

        if automation.type in ignorable_types:
            return
        self.is_volume = True

        self.vol1 = p1.value
        self.vol2 = p2.value

        # constant is an special value that should ignore p2
        # in fades it's only used in p2 to indicate that volume lasts
        # (ex. fade-in: p1={0.0s, 0.0 vol, linear}, p2={4.0s, 1.0 vol, constant})
        if p1.interp == 9:
            self.vol2 = self.vol1

        # normalize volumes
        if version < _AUTOMATION_NEW_VOLUME_VERSION:
            # convert -96.0 .. 0.0 .. 96.0 dB to volume (scaling "dB_96_3")
            self.vol1 = pow(10.0, self.vol1 / 20.0)
            self.vol2 = pow(10.0, self.vol2 / 20.0)
        else:
            if automation.type == 0: # volume
                # convert -1.0 .. 0.0 .. 1.0 to 0.0 .. 1.0 .. 2.0 (scaling "dB")
                self.vol1 += 1.0
                self.vol2 += 1.0
            else: # fades
                # standard 0.0 .. 1.0
                pass

        # some points are just used to delay with no volume change
        # note that constant different volumes exists (ex. -0.24 .. -0.24 on doomy ternal)
        if self.vol1 == 1.0 and self.vol2 == 1.0:
            return

        # approximate curves
        if self.vol1 < self.vol2:
            interpolations = _TXTP_INTERPOLATIONS_FADEIN
        else:
            interpolations = _TXTP_INTERPOLATIONS_FADEOUT
        self.shape = interpolations.get(p1.interp, '{')

        self.time1 = p1.time
        self.time2 = p2.time - p1.time

        # clamp times (occasionally Wwise makes tiny negative values on what seems an editor hiccup, shouldn't matter)
        if self.time1 < 0:
            self.time1 = 0.0
        if self.time2 < 0:
            self.time2 = 0.0

        self.usable = True

# Transform wwise automations to txtp envelopes.
# Wwise defines points (A,B,C) and autocalcs combos like (A,B),(B,C),
# but for txtp we need to pre-make combos in the format of:
# - ch(type)(position)(time-start)+(time-length) [simpler fades]
# - ch^(volume-start)~(volume-end)=(shape)@(time-pre)~(time-start)+(time-length)~(time-last) [complex volumes]
class NodeEnvelopeList(object):
    def __init__(self, sound):
        self.empty = False
        self._envelopes = []
        self._build(sound)

    def _build(self, sound):
        if not sound:
            return
        if sound.automations and not sound.source:
            raise ValueError("unexpected automations without source")
        if not sound.source:
            return
        automations = sound.automations
        version = sound.source.version 
        if not automations or not version:
            return

        for automation in automations:
            max = len(automation.points)
            for i in range(0, max):
                if (i + 1 >= max):
                    continue
                # envelopes are made of N points, though in fade-in and fade-out types there are only 2 points (start>end)
                p1 = automation.points[i]
                p2 = automation.points[i+1]

                envelope = NodeEnvelope(automation, p1, p2, version)
                if not envelope.usable or not envelope.is_volume:
                    continue

                self._envelopes.append(envelope)
        self.empty = len(self._envelopes) <= 0

    def items(self):
        return self._envelopes

    def pad(self, pad_time):
        for envelope in self._envelopes:
            envelope.time1 += pad_time
