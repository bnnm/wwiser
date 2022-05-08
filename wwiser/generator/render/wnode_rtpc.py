import math

# RTPC helpers
#
# RTPCs are a graph/curve of params, where passing a value (usually a gamevar) returns another
# (usually a defined property like volume), to calculate expected values in real time.
#  For example, PARAM_HP at 100~30 could be volume 100, at 30~0 volume decreses progressively.

_GRAPH_NEW_SCALING = 72 #>=


# Represents a graph point.
# Each point is discrete yet connected to next point via easing function
# ex. point1: from=0.0, to=0.0, interp=sine
#     point2: from=1.0, to=1.0, interp=constant
# with both you have a fade in from 0.0..1.0, changing volume from silence to full in a sine curve
class _AkGraphPoint(object):
    def __init__(self, npoint):
        self.x = 0
        self.y = 0
        self.i = 0

        if not npoint:
            return
        self.x = npoint.find(name='From').value() #x-axis (input value)
        self.y = npoint.find(name='To').value() #y-axis (output value)
        self.i = npoint.find(name='Interp').value() #easing function between points

# Set of points, that can convert a passed value to another based on interpolations.
# input/output is always a float.
# Somewhat adapted from original functions
class _AkGraph(object):
    def __init__(self, nbase, scaling):
        self.points = []
        self.scaling = scaling
        self.version = 0

        if not nbase:
            return
        self.version = nbase.get_root().get_version()

        npoints = nbase.finds(name='AkRTPCGraphPoint')
        for npoint in npoints:
            p = _AkGraphPoint(npoint) 
            self.points.append(p)

    #CAkConversionTable::ConvertInternal
    def get(self, v):
        v = self._find(v)
        v = self._scale(v)
        return v

    def _find(self, v):
        ps = self.points

        if not ps: #doesn't seem handled in Wwise
            return 0.0

        if len(ps) == 1:
            return ps[0].y

        for i in range(len(ps)):
            p1 = ps[i]

            if p1.x >= v: #min
                return p1.y
            if i + 1 == len(ps): #max
                return p1.y

            p2 = ps[i+1]
            if p2.x > v: #pair found
                if p1.i == 4: #linear
                    v = self._AkMath__InterpolateNoCheck(p1.x, p1.y, p2.x, p2.y, v)
                elif p1.i == 9: #constant
                    v = p1.y
                else:
                    v = self._AkInterpolation__InterpolateNoCheck( (v - p1.x) / (p2.x - p1.x), p1.y, p2.y, p1.i )
                return v

        raise ValueError("point not found") #should fall in min/max

    def _AkMath__InterpolateNoCheck(self, lowerX, lowerY, upperX, upperY, v):
        return (upperY - lowerY) * ((v - lowerX) / (upperX - lowerX)) + lowerY

    def _AkInterpolation__InterpolateNoCheck(self, timeRatio, initialVal, targetVal, eFadeCurve):
        i = eFadeCurve
        if i == 0: #Log3
            return (1.0 - timeRatio) * (1.0 - timeRatio) * (1.0 - timeRatio) * (initialVal - targetVal) + targetVal

        if i == 1: #Sine
            v1 = (1.5707964 * timeRatio) * (1.5707964 * timeRatio)
            v2 = (v1 * -0.00018363654 + 0.0083063254) * v1 + -0.16664828
            v3 = v2 * v1 + 0.9999966
            return v3 * (1.5707964 * timeRatio) * (targetVal - initialVal) + initialVal

        if i == 2: #Log1
            return (timeRatio - 3.0) * timeRatio * 0.5 * (initialVal - targetVal) + initialVal

        if i == 3: #InvSCurve
            if timeRatio > 0.5:
                v1 = 3.1415927 - (3.1415927 * timeRatio)
                v2 = (v1 * v1 * -0.00009181827 + 0.0041531627) * (v1 * v1) + -0.083324142
                v3 = (1.0 - (v2 * (v1 * v1) + 0.4999983) * v1)
                return v3 * (targetVal - initialVal) + initialVal
            else:
                v1 = (3.1415927 * timeRatio) * (3.1415927 * timeRatio)
                v2 = (v1 * -0.00009181827 + 0.0041531627) * v1 + -0.083324142
                v3 = (v2 * v1 + 0.4999983) * (3.1415927 * timeRatio)
                return v3 * (targetVal - initialVal) + initialVal

        if i == 4: #Linear
            return (targetVal - initialVal) * timeRatio + initialVal

        if i == 5: #SCurve
            v1 = (3.1415927 * timeRatio) * (3.1415927 * timeRatio)
            v2 = (v1 * 0.00048483399 + -0.01961384) * v1 + 0.24767479
            v3 = v2 * v1 + 0.00069670216
            return v3 * (targetVal - initialVal) + initialVal

        if i == 6: #Exp1
            return (timeRatio + 1.0) * timeRatio * 0.5 * (targetVal - initialVal) + initialVal

        if i == 7: #SineRecip
            v1 = (1.5707964 * timeRatio) * (1.5707964 * timeRatio)
            v2 = (v1 * -0.0012712094 + 0.04148775) * v1 + -0.49991244
            v3 = v2 * v1 + 0.99999332
            return v3 * (initialVal - targetVal) + targetVal

        if i == 8: #Exp3
            v3 = timeRatio * timeRatio * timeRatio
            return v3 * (targetVal - initialVal) + initialVal

        #if i == 9: #Constant (external)
        #    return 0 #external
        raise ValueError("unknown interpolation")

    #CAkConversionTable::ApplyCurveScaling
    def _scale(self, v):
        sc = self.scaling
        if self.version < _GRAPH_NEW_SCALING:
            if sc == 0: #no scaling
                pass

            elif sc == 1: #db_255 (v46<=) / not implemented (rest)
                raise ValueError("unknown rtpc")

            elif sc == 2 or sc == 4: # dB_96_3: rescaled from -96db to +96db (4 is same but errors on min/max)
                # 0 = 0db, 96.3 = 96db, -96 = -96db, 20.0 = 2db, 50.0=6db, etc
                v = self._LinearMutingTodBMuting96(v)

            elif sc == 3: #rescaled from 20.0 to 20000.0
                v = self._linearToFrequency_20_20000(v)

            else:
                raise ValueError("unknown rtpc scaling")

        else:
            if sc == 0: #no scaling
                pass

            elif sc == 1: #not defined
                raise ValueError("unknown rtpc")

            elif sc == 2:
                v = self._ScalingFromLin_dB(v)

            elif sc == 3:
                v = self._ScalingFromLog(v)

            elif sc == 4:
                v = self._dBToLin(v)

            else:
                raise ValueError("unknown rtpc scaling")

        return v

    def _dBToReal(self, v):
        return math.pow(10.0, v / 20.0)

    def _realTodB(self, v):
        return math.log10(v) * 20.0

    def _LinearMutingTodBMuting96(self, v):
        if v == 0.0:
            return v

        max = +96.300003
        if v >= max:
            return max
        min = -96.300003
        if v <= min:
            return min
        
        if v > 0.0:
            v = (96.3 - v) / 96.3
            return -self._realTodB(v)
        else:
            v = (v + 96.3) / 96.3
            return +self._realTodB(v)

    def _linearToFrequency_20_20000(self, v):
        max = 20000.0
        if v >= max:
            return max
        min = 20.0
        if v <= min:
            return min

        v = (v - 20.0) / 6660.0 + 1.301029995663981
        return math.pow(10.0, v)

    def _ScalingFromLin_dB(self, v):
        max = 1.0
        if v >= max:
            v = max
        min = -1.0
        if v <= min:
            v = min

        # TODO: as found in code, but makes no sense since it should be +-1.0 = +-96.3db, +-0.5=6db
        # but it makes +-1.0 = +-6.0db
        #vabs = abs(v)
        #db = math.log10(vabs + 1.0) * 20.0 #~FastLinTodB + ~FastLog10?
        #if v < 0:
        #    db = -db

        if v == -1.0:
            db = -96.3
        else:
            db = math.log10(v + 1.0) * 20.0 #~FastLinTodB + ~FastLog10?
        return db

    def _ScalingFromLog(self, v):
        return math.pow(10.0, v / 20.0) #~FastPow10?

    def _dBToLin(self, v):
        return math.pow(10.0, v * 0.050000001) #~FastPow10?


_RTPC_NEW_ACCUM = 120 #>=

class AkRtpc(object):
    def __init__(self, nrtpc):
        self.is_volume = False
        self.nrtpc = nrtpc

        nparam = nrtpc.find1(name='ParamID')
        if nparam.value() != 0: #volume
            return #not usable for txtp

        self.is_volume = True

        self.version = nrtpc.get_root().get_version()

        self.nid = nrtpc.find1(name='RTPCID') #name/id
        self.id = self.nid.value()

        scaling = nrtpc.find1(name='eScaling').value()
        self.graph = _AkGraph(nrtpc, scaling)

        #rtpcType: game parameter/midi/modulator, probably not important (>=112)

        naccum = nrtpc.find1(name='rtpcAccum') #~113
        self.accum = 0
        if naccum:
            self.accum = naccum.value()


    def get(self, x, value):
        if not self.is_volume:
            return value
        y = self.graph.get(x)

        if value is None:
            value = 0

        # accum type seems to affect how value is added to current, but volume looks fixed to "additive",
        # ignoring actual value that may be set to "exclusive" (at least in Wwise editor value modifies
        # current volume). Docs also mention property behavior is fixed per property
        return y + value

        #if self.version < _RTPC_NEW_ACCUM:
        #    if self.accum == 0: #exclusive
        #        return y + value #??? (sounds better with volumes?)
        #    if self.accum == 1: #additive
        #        return y + value
        #    if self.accum == 2: #multiply
        #        return y * value
        #else:
        #    if self.accum == 1: #exclusive
        #        return y + value #??? (sounds better with volumes?)
        #    if self.accum == 2: #additive
        #        return y + value
        #    if self.accum == 3: #multiply
        #        return y * value
        #    if self.accum == 4: #boolean
        #        return y or value #???
        #raise ValueError("unknown accum")

    def minmax(self):
        ps = self.graph.points
        if not ps:
            return (0.0, 0.0)

        p1 = ps[0]
        if len(ps) == 1:
            p2 = p1
        else:
            p2 = ps[len(ps)-1]

        return (p1.x, p2.x)

    def min(self):
        return self.minmax()[0]

    def max(self):
        return self.minmax()[1]
