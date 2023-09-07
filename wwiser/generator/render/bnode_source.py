from .. import wlang

_CODEC_EXTENSION_NEW_VERSION = 62 #>=
_CODEC_EXTENSION_NEW = 'wem'
_CODEC_EXTENSIONS_OLD = {
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

# Newer UE4 WW plugin allows "event-based packaging", that is, having a single .bnk with one event and
# memory/prefetch/streamed wem in .uassets/ubulks. Plugin handles this transparently so user only defines
# events and doesn't need to create/manage bnks manually (plugin also allows 1 bnk with N events).
# Memory/prefetch/streams audio is still marked as such, but since flags are in the .uasset we don't know here
# which is which (all look like loose .wem). Incidentally bank's hashname seems to be SB_<guid> (except Init.bnk).
_MEMORY_ASSET_NEW = 135 #>=

# Hitman (2016) also seems to have a custom loader were RAM wems are separate
_MEMORY_ASSET_CUSTOM = [
    113
]



_PLUGIN_SILENCE = set([
    0x00650002, #standard
    0x00000000, #probably a removed plugin (South Park: Stick of Truth)
])

_PLUGIN_GAIN = 0x008B0003

_PLUGIN_IGNORABLE = set([
    0x01950002,
    0x01990002,
])

PLUGIN_NAME = {
    0x00640002: 'sine',
    0x00650002: 'silence',
    0x00660002: 'tone',
    0x00000000: 'removed',
}

class AkBankSourceData(object):
    def __init__(self, nbnksrc, src_sid):
        self._build_base(nbnksrc, src_sid)
        self._build_media(nbnksrc)
        self._build_plugin()
        self._build_extension()

        # not done by default to minimize some node finding
        #self._load_lang()
        self._lang_loaded = False
        self._lang_shortname = ''
        self._lang_fullname = ''


    def _build_base(self, nbnksrc, src_sid):
        self.src_sid = src_sid
        self.nsrc = nbnksrc
        self.nplugin = nbnksrc.find(name='ulPluginID') #source type
        self.nstreamtype = nbnksrc.find(name='StreamType') #bank/stream

        self.version = None
        if self.nsrc:
            self.version = self.nsrc.get_root().get_version()

        #0=bnk (always), 1/2=prefetch<>stream (varies with version)
        self.internal = (self.nstreamtype.value() == 0)
        # no actual detection, just to indicate may be ignored
        self.internal_ebp = self.internal and self.version and (
            self.version >= _MEMORY_ASSET_NEW or self.version in _MEMORY_ASSET_CUSTOM)

        # plugin info
        nsize = self.nsrc.find(name='uSize')
        self.plugin_size = None
        if nsize:
            self.plugin_size = nsize.value()


    def _build_media(self, nbnksrc):
        #AkMediaInformation
        self.nsourceid = nbnksrc.find(name='sourceID')
        self.nfileid = nbnksrc.find(name='uFileID') #optional
        self.nlang = nbnksrc.find(name='bIsLanguageSpecific') #flags
        self._lang_loaded = False

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


    def _build_plugin(self):
        # plugin info
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
        self.plugin_ignorable = (plugin in _PLUGIN_IGNORABLE)

        # info 
        self.is_plugin_silence = (plugin in _PLUGIN_SILENCE)

        # config loaded later
        self.plugin_fx = None


    # each source may use its own extension
    def _build_extension(self):
        if self.plugin_id:
            self.extension = None
            self.extension_alt = None
            return

        # rare but possible to have sources without tid/codec (ex. AoT2 Car_Cestructible.bnk)
        if not self.plugin_codec:
            self.extension = None
            self.extension_alt = None
            return

        if self.version >= _CODEC_EXTENSION_NEW_VERSION:
            #wmid seem to be use .wem but also .wmid sometimes?
            self.extension = _CODEC_EXTENSION_NEW
        else:
            self.extension = _CODEC_EXTENSIONS_OLD.get(self.plugin_codec)
            if not self.extension:
                raise ValueError("extension not found for old version codec %s, tid=%s (report)" % (self.plugin_codec, self.tid))

        if   self.extension == 'ogg':
            self.extension_alt = 'logg'
        elif self.extension == 'wav':
            self.extension_alt = 'lwav'
        else:
            self.extension_alt = self.extension

    #  language subdir or nothing if source doesn't depend on language
    def lang_fullname(self):
        if not self._lang_loaded:
            self._load_lang()
        return self._lang_fullname

    # language short name or nothing if source doesn't depend on language
    def lang_shortname(self):
        if not self._lang_loaded:
            self._load_lang()
        return self._lang_shortname

    def _load_lang(self):
        self._lang_loaded = True

        # bank may have language value and flag set per source (not set for internals?)
        # - external source + flag set = use subdir
        # - internal source + bank has language = use subdir, since banks will be names same for all languages
        if not self.internal and (not self.nlang or self.nlang.value() == 0):
            return

        lang = wlang.Lang(self.nsrc)
        self._lang_fullname = lang.fullname
        self._lang_shortname = lang.shortname
        

class CAkFx(object):
    def __init__(self, node, plugin_id):
        self.duration = 1.0 * 1000.0 #default?
        self.plugin_id = plugin_id
        self.gain = 0
        self.lfe = 0
        self._build(node)

    def _build(self, node):
        if not node:
            return

        #FxBaseInitialValues
        # fxID (may exist in AkFXCustom, or external in older versions)
        # uSize
        # Ak*FXParams

        if self.plugin_id == _PLUGIN_SILENCE:
            nparams = node.find1(name='AkFXSrcSilenceParams')
            ndur = nparams.find(name='fDuration')
            self.duration = ndur.value()  * 1000.0 #to ms for consistency

        if self.plugin_id == _PLUGIN_GAIN:
            nparams = node.find1(name='AkGainFXParams')
            ngain = nparams.find(name='fFullbandGain')
            nlfe = nparams.find(name='fLFEGain')
            self.gain = ngain.value()
            self.lfe = nlfe.value()
