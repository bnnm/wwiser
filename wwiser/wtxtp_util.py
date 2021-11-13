import math

# common config from all nodes to pass around
#
# loop_flag = 0 in Wwise means "full loop or use loop points of file has (if file is sfx)",
# and 1 means "don't loop even if the file has loop points" (like xma/dsp)
# (>N also means "loop N times", but sounds shouldn't use this, only groups)
class NodeConfig(object):
    def __init__(self):
        self.loop = None
        self.volume = None
        self.makeupgain = None
        self.pitch = None
        self.delay = None
        self.idelay = None
        self.crossfaded = False #RPTC/state controlled silence
        self.rtpcs = []
        #markers
        self.duration = None
        self.entry = None
        self.exit = None
        self.exit = None

        # states that when active silence group
        self.silence_states = []

    def add_silence_state(self, ngroup, nvalue):
        item = (ngroup, nvalue)
        self.silence_states.append(item)


#common audio object with config
class NodeSound(object):
    def __init__(self):
        self.source = None #original source info (may not exist for silence)
        self.nsrc = None #to get root bank
        self.silent = False
        self.automations = None

        #clips can be modded by the engine (regular sounds are pre-changed when saved to .wem)
        self.clip = False
        self.fpa = 0  #moves track from start (>0=right, <0=left)
        self.fbt = 0  #mods beginning (>0=trim, <0=add begin repeat)
        self.fet = 0  #mods end (<0=trim, >0=add end repeat)
        self.fsd = 0  #original file duration (for calcs)

class NodeTransition(object):
    def __init__(self):
        self.play_before = False
        self.play_after = False
        self.entry_type = 0
        self.exit_type = 0
        self.fadein_type = None
        self.fadein_time = 0
        self.fadeout_type = None
        self.fadeout_time = 0
        self.fadein_pos = 0
        self.fadeout_pos = 0

class NodeStinger(object):
    def __init__(self):
        self.node = None
        self.ntrigger = None
        self.ntid = None

#******************************************************************************

CODEC_EXTENSION_NEW_VERSION = 62 #>=
CODEC_EXTENSION_NEW = 'wem'
CODEC_EXTENSIONS_OLD = {
  0x01: "wav", #PCM
  0x02: "wav", #ADPCM
  0x03: "xma", #XMA
  0x04: "ogg", #VORBIS
  0x05: "wav", #WIIADPCM
 #0x06: "???", #?
  0x07: "wav", #PCMEX
 #0x08: "---", #EXTERNAL_SOURCE
 #0x09: "???", #XWMA
 #0x0A: "???", #AAC
 #0x0B: "---", #FILE_PACKAGE
 #0x0C: "???", #ATRAC9
 #0x0D: "???", #VAG/HE-VAG
 #0x0E: "---", #PROFILERCAPTURE
 #0x0F: "---", #ANALYSISFILE
}

LANGUAGE_IDS = {
    0x00: "SFX",
    0x01: "Arabic",
    0x02: "Bulgarian",
    0x03: "Chinese(HK)",
    0x04: "Chinese(PRC)",
    0x05: "Chinese(Taiwan)",
    0x06: "Czech",
    0x07: "Danish",
    0x08: "Dutch",
    0x09: "English(Australia)",
    0x0A: "English(India)",
    0x0B: "English(UK)",
    0x0C: "English(US)",
    0x0D: "Finnish",
    0x0E: "French(Canada)",
    0x0F: "French(France)",
    0x10: "German",
    0x11: "Greek",
    0x12: "Hebrew",
    0x13: "Hungarian",
    0x14: "Indonesian",
    0x15: "Italian",
    0x16: "Japanese",
    0x17: "Korean",
    0x18: "Latin",
    0x19: "Norwegian",
    0x1A: "Polish",
    0x1B: "Portuguese(Brazil)",
    0x1C: "Portuguese(Portugal)",
    0x1D: "Romanian",
    0x1E: "Russian",
    0x1F: "Slovenian",
    0x20: "Spanish(Mexico)",
    0x21: "Spanish(Spain)",
    0x22: "Spanish(US)",
    0x23: "Swedish",
    0x24: "Turkish",
    0x25: "Ukrainian",
    0x26: "Vietnamese",
}

LANGUAGE_HASHNAMES = {
    393239870: "SFX",
    3254137205: "Arabic",
    4238406668: "Bulgarian",
    218471146: "Chinese(HK)",
    3948448560: "Chinese(PRC)",
    2983963595: "Chinese(Taiwan)",
    877555794: "Czech",
    4072223638: "Danish",
    353026313: "Dutch",
    144167294: "English(Australia)",
    1103735775: "English(India)",
    550298558: "English(UK)",
    684519430: "English(US)",
    50748638: "Finnish",
    1024389618: "French(Canada)",
    323458483: "French(France)",
    4290373403: "German",
    4147287991: "Greek",
    919142012: "Hebrew",
    370126848: "Hungarian",
    1076167009: "Indonesian",
    1238911111: "Italian",
    2008704848: "Japanese",
    4224429355: "Japanese(JP)",
    3391026937: "Korean",
    3647200089: "Latin",
    701323259: "Norwegian",
    559547786: "Polish",
    960403217: "Portuguese(Brazil)",
    3928554441: "Portuguese(Portugal)",
    4111048996: "Romanian",
    2577776572: "Russian",
    3484397090: "Slovenian",
    3671217401: "Spanish(Mexico)",
    235381821: "Spanish(Spain)",
    4148950150: "Spanish(US)",
    771234336: "Swedish",
    4036333791: "Turkish",
    4065424201: "Ukrainian",
    2847887552: "Vietnamese",
}

LANGUAGE_SHORTNAMES = {
    "SFX": 'sfx',
    "Arabic": 'ar',
    "Bulgarian": 'bg',
    "Chinese(HK)": 'zh-hk',
    "Chinese(PRC)": 'zh-cn',
    "Chinese(Taiwan)": 'zh-tw',
    "Czech": 'cs',
    "Danish": 'da',
    "Dutch": 'nl',
    "English(Australia)": 'en-au',
    "English(India)": 'en-in', #?
    "English(UK)": 'en', #en-gb
    "English(US)": 'us', #en-us
    "Finnish": 'fi',
    "French(Canada)": 'fr-ca',
    "French(France)": 'fr',
    "German": 'de',
    "Greek": 'el',
    "Hebrew": 'he',
    "Hungarian": 'hu',
    "Indonesian": 'id',
    "Italian": 'it',
    "Japanese": 'ja',
    "Japanese(JP)": 'ja',
    "Korean": 'ko',
    "Latin": 'la', #what (used in SM:WoS for placeholder voices, that are reversed audio of misc voices)
    "Norwegian": 'no',
    "Polish": 'pl',
    "Portuguese(Brazil)": 'pt-br',
    "Portuguese(Portugal)": 'pt',
    "Romanian": 'ro',
    "Russian": 'ru',
    "Slovenian": 'sl',
    "Spanish(Mexico)": 'es-mx',
    "Spanish(Spain)": 'es',
    "Spanish(US)": 'es-us',
    "Swedish": 'sv',
    "Turkish": 'tr',
    "Ukrainian": 'uk',
    "Vietnamese": 'vi',
}

PLUGIN_IGNORABLE = set([
    0x01950002,
    0x01990002,
])

PLUGIN_NAME = {
    0x00640002: 'sine',
    0x00650002: 'silence',
    0x00660002: 'tone',
}

class NodeSource(object):
    def __init__(self, nbnksrc, src_sid):
        self.src_sid = src_sid
        self.nsrc = nbnksrc
        self.nplugin = nbnksrc.find(name='ulPluginID')
        self.nstreamtype = nbnksrc.find(name='StreamType')
        self.nsourceid = nbnksrc.find(name='sourceID')
        self.nfileid = nbnksrc.find(name='uFileID')
        self.nlang = nbnksrc.find(name='bIsLanguageSpecific')
        self._lang_loaded = False

        self.version = None
        if self.nsrc:
            self.version = self.nsrc.get_root().get_version()

        #0=bnk (always), 1/2=prefetch<>stream (varies with version)
        self.internal = (self.nstreamtype.value() == 0)

        if self.nfileid:
            # in older games (<=112) fileID exists and can be different from sourceID
            # (happens when clipped trims are different), and has multiple meanings:
            # - bankID for internals, with sourceID being bank's media ID
            # - fileID for streams (.wem number), with sourceID being an info ID
            if self.internal: #unify with newer version
                #self.nbankid = self.nfileid #could be useful to find/print errors?
                self.nfileid = self.nsourceid
        else:
            # in newer games only sourceID is used (.wem number)
            self.nfileid = self.nsourceid
        self.tid = self.nfileid.value()

        self._plugin()
        self._extension()
        # not done by default to minimize some node finding since this option is uncommon
        #self._load_lang()
        self._lang_name = ''
        self._subdir = ''

    # plugin info
    def _plugin(self):
        plugin = self.nplugin.value()

        #company  = (plugin >> 4) & 0x03FF
        self.plugin_type = (plugin >> 0) & 0x000F
        self.plugin_codec = (plugin >> 16) & 0xFFFF

        # id is defined at runtime externally ("External Source" plugin)
        if self.plugin_codec == 0x08:
            self.plugin_external = True
            self.internal = False
        else:
            self.plugin_external = False

        if self.plugin_type != 0x01: #codec
            self.plugin_id = plugin
            self.plugin_name = PLUGIN_NAME.get(plugin, "%08x" % (plugin))
        else:
            self.plugin_id = None
            self.plugin_name = None

        # there is basic detection in vgmstream but not good enough
        self.plugin_wmid = (plugin == 0x00100001) #MIDI

        # plugins for internal use only and don't generate sound
        self.plugin_ignorable = (plugin in PLUGIN_IGNORABLE)

        # config loaded later
        self.plugin_fx = None


    # each source may use its own extension
    def _extension(self):
        if self.plugin_id:
            self.extension = None
            self.extension_alt = None
            return

        # rare but possible to have sources without tid/codec (ex. AoT2 Car_Cestructible.bnk)
        if not self.plugin_codec:
            self.extension = None
            self.extension_alt = None
            return

        if self.version >= CODEC_EXTENSION_NEW_VERSION:
            #wmid seem to be use .wem but also .wmid sometimes?
            self.extension = CODEC_EXTENSION_NEW
        else:
            self.extension = CODEC_EXTENSIONS_OLD.get(self.plugin_codec)
            if not self.extension:
                raise ValueError("extension not found for old version codec %s, tid=%s (report)" % (self.plugin_codec, self.tid))

        if   self.extension == 'ogg':
            self.extension_alt = 'logg'
        elif self.extension == 'wav':
            self.extension_alt = 'lwav'
        else:
            self.extension_alt = self.extension

    #  language subdir or nothing if source doesn't depend on language
    def subdir(self):
        if not self._lang_loaded:
            self._load_lang()
        return self._subdir

    # language short name or nothing if source doesn't depend on language
    def lang(self):
        if not self._lang_loaded:
            self._load_lang()
        return self._lang_name

    def _load_lang(self):
        self._lang_loaded = True

        # bank may have language value and flag set per source (not set for internals?)
        # - external source + flag set = use subdir
        # - internal source + bank has language = use subdir, since banks will be names same for all languages
        if not self.internal and (not self.nlang or self.nlang.value() == 0):
            return

        nroot = self.nsrc.get_root()
        nlangid = nroot.find1(name='BankHeader').find1(name='dwLanguageID')
        version = nroot.get_version()

        lang_value = nlangid.value()
        if version <= 122: #set of values
            lang_name = LANGUAGE_IDS.get(lang_value)
        else: #set of hashed names
            # typical values but languages can be anything (redefined in project options)
            lang_name = LANGUAGE_HASHNAMES.get(lang_value)
            if not lang_name: #try loaded names (ex. Xenoblade DE uses "en" and "jp")
                lang_name = nlangid.get_attr('hashname')

        if not lang_name:
            lang_name = "language-%s" % (lang_value)

        lang_short = LANGUAGE_SHORTNAMES.get(lang_name, lang_name)
        if lang_short == 'sfx':
            lang_short = ''
        self._lang_name = lang_short

        if lang_name == 'SFX':
            subdir = ''
        else:
            subdir = "%s/" % (lang_name)
        self._subdir = subdir


class NodeFx(object):
    def __init__(self, node, plugin_id):
        self.duration = 1.0 * 1000.0

        if not node:
            return

        if plugin_id == 0x00650002: #silence
            nparams = node.find1(name='AkFXSrcSilenceParams')
            ndur = nparams.find(name='fDuration')
            self.duration = ndur.value()  * 1000.0 #to ms for consistency


ENVELOPE_NEW_VERSION = 112 #>= #todo unsure

INTERPOLATIONS = {
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
        self.vol1 = None
        self.vol2 = None
        self.shape = None
        self.time1 = None
        self.time2 = None
        if not am or not p1 or not p2:
            return

        # LFE work differently        
        if version < ENVELOPE_NEW_VERSION:
            ignorable_types = [1] #LFE
        else:
            ignorable_types = [1,2] #LFE,HFE
        if am.type in ignorable_types:
            return

        self.vol1 = p1.value
        self.vol2 = p2.value

        # constant is an special value that should ignore p2
        if (p1.interp == 9):
            self.vol2 = self.vol1

        # normalize volumes
        if version < ENVELOPE_NEW_VERSION:
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
        self.shape = INTERPOLATIONS.get(p1.interp, '{')

        self.time1 = p1.time + base_time
        self.time2 = p2.time - p1.time

        self.usable = True

###############################################################################

GRAPH_NEW_SCALING = 72 #>=


# Represents a graph point.
# Each point is discrete yet connected to next point via easing function
# ex. point1: from=0.0, to=0.0, interp=sine
#     point2: from=1.0, to=1.0, interp=constant
# with both you have a fade in from 0.0..1.0, changing volume from silence to full in a sine curve
class NodeGraphPoint(object):
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
class NodeGraph(object):
    def __init__(self, nbase, scaling):
        self.points = []
        self.scaling = scaling
        self.version = 0

        if not nbase:
            return
        self.version = nbase.get_root().get_version()

        npoints = nbase.finds(name='AkRTPCGraphPoint')
        for npoint in npoints:
            p = NodeGraphPoint(npoint) 
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
        if self.version < GRAPH_NEW_SCALING:
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


RTPC_NEW_ACCUM = 120 #>=

class NodeRtpc(object):
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
        self.graph = NodeGraph(nrtpc, scaling)

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

        #if self.version < RTPC_NEW_ACCUM:
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
