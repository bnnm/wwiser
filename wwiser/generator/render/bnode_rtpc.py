import math

# RTPC (Real-time Parameter Controls) helpers
#
# RTPCs are a graph/curve of params, where passing a value (usually a gamevar) returns another
# (usually a defined property like volume), to calculate expected values in real time.
#  For example, PARAM_HP at 100~30 could be volume 100, at 30~0 volume decreses progressively.
#
# It's possible to make dummy RTPCs that don't change anything (constant value 0) but probably
# aren't common enough to bother detecting.

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
                raise ValueError("unknown graph scaling")

            elif sc == 2 or sc == 4: # dB_96_3: rescaled from -96db to +96db (4 is same but errors on min/max)
                # 0 = 0db, 96.3 = 96db, -96 = -96db, 20.0 = 2db, 50.0=6db, etc
                v = self._LinearMutingTodBMuting96(v)

            elif sc == 3: #rescaled from 20.0 to 20000.0
                v = self._linearToFrequency_20_20000(v)

            else:
                raise ValueError("unknown graph scaling")

        else:
            if sc == 0: #no scaling
                pass

            elif sc == 1: #not defined
                raise ValueError("unknown graph scaling")

            elif sc == 2:
                v = self._ScalingFromLin_dB(v)

            elif sc == 3:
                v = self._ScalingFromLog(v)

            elif sc == 4:
                v = self._dBToLin(v)

            else:
                raise ValueError("unknown graph scaling")

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

        # as found in code, but makes no sense since it should be +-1.0 = +-96.3db, +-0.5=6db
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


# ---------------------------------------------------------

#_RTPC_NEW_ACCUM = 125 #>= #adds "none"

class AkRtpc(object):
    def __init__(self, nrtpc):
        self.nid = None
        self.id = None
        self.graph = None
        self.is_gamevar = False
        self.nparam = None

        self._build(nrtpc)

    def _build(self, nrtpc):
        self.nid = nrtpc.find1(name='RTPCID') #gamevar name/id
        self.id = self.nid.value()

        # game parameter/midi/modulator, probably not important (>=112)
        ntype = nrtpc.find1(name='rtpcType')
        self.is_gamevar = not ntype or ntype.value() == 0

        self.nparam = nrtpc.find1(name='ParamID')
        self._parse_props(self.nparam)

        scaling = nrtpc.find1(name='eScaling').value()
        self.graph = _AkGraph(nrtpc, scaling)

        naccum = nrtpc.find1(name='rtpcAccum') #112
        self._parse_accum(naccum)

    def _parse_props(self, nparam):
        # see CAkProps, but RTPC's props are a bit different (different IDs, more limited like no Loop prop)

        valuefmt = nparam.get_attrs().get('valuefmt')

        # relative
        self.is_volume = '[Volume]' in valuefmt or (nparam.value() == 0) #volume prop
        self.is_busvolume = '[BusVolume]' in valuefmt
        self.is_outputbusvolume = '[OutputBusVolume]' in valuefmt
        self.is_makeupgain = '[MakeUpGain]' in valuefmt
        self.is_pitch = '[Pitch]' in valuefmt
        self.is_playbackspeed = '[PlaybackSpeed]' in valuefmt #multiplicative
        # absolute
        # (could handle positioning params)
        # behavior
        self.is_delay = '[InitialDelay]' in valuefmt
        # other props: "LFE", "LPF", "HPF", etc

    def _parse_accum(self, naccum):
        self._accum_exc = False
        self._accum_add = False
        self._accum_mul = False
        self._accum_bln = False

        if not naccum: #older:  fixed per property
            self._accum_add = self.is_volume or self.is_busvolume or self.is_outputbusvolume or self.is_makeupgain or self.is_pitch
            self._accum_mul = self.is_playbackspeed
            self._accum_exc = self.is_delay
            return

        valuefmt = naccum.get_attrs().get('valuefmt')
        if '[None]' in valuefmt: #not seen
            raise ValueError("unknown rtpc None")

        self._accum_exc = '[Exclusive]' in valuefmt #initial delay
        self._accum_add = '[Additive]' in valuefmt #volumes, most others
        self._accum_mul = '[Multiply]' in valuefmt #playback speed
        self._accum_bln = '[Boolean]' in valuefmt #bypass FX flag

    def is_usable(self, apply_bus):
        if apply_bus and (self.is_busvolume or self.is_outputbusvolume):
            return True
        return self.is_volume or self.is_makeupgain or self.is_delay

    # get resulting value: X = game parameter, Y = Wwise property
    def get(self, x):
        y = self.graph.get(x)
        if self.is_delay:
            y = y * 1000.0 #idelay is float in seconds to ms
        return y

    def accum(self, y, current_value):
        # Accum type affects how values are added to current. Property behavior is fixed (regular props
        # like volume are additive, actions like delay are exclusive, etc) but also described in the RTPC.
        if current_value is None:
            current_value = 0

        if self._accum_exc == 0: #exclusive (RTPC has priority)
            return y
        if self._accum_add == 1: #additive
            return y + current_value
        if self._accum_mul == 2: #multiply
            return y * current_value
        if self._accum_bln == 4: #boolean
            return y or current_value #???
        raise ValueError("unknown accum")


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


class AkRtpcList(object):
    def __init__(self, node):
        self.valid = False
        self._rtpcs = []
        self._usables = None
        self._build(node)

    def empty(self):
        return self._rtpcs.empty()

    def _build(self, node):
        if not node:
            return
        nrtpcs = node.finds(name='RTPC')
        if not nrtpcs:
            return
        self.valid = True
        for nrtpc in nrtpcs:
            rtpc = AkRtpc(nrtpc)
            #if not rtpc.is_gamevar:
            #    continue

            self._rtpcs.append(rtpc)

    def get_rtpc(self, id):
        for rtpc in self._rtpcs:
            if rtpc.id == id:
                return rtpc
        return None

    def get_rtpcs(self):
        return self._rtpcs

    def get_usable_rtpcs(self, apply_bus):
        if self._usables is None:
            items = []
            for rtpc in self._rtpcs:
                if rtpc.is_usable(apply_bus):
                    items.append(rtpc)
            self._usables = items
        return self._usables
