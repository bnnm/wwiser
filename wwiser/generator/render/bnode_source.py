
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

_LANGUAGE_IDS = {
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

_LANGUAGE_HASHNAMES = {
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

_LANGUAGE_SHORTNAMES = {
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

_PLUGIN_SILENCE = 0x00650002

_PLUGIN_IGNORABLE = set([
    0x01950002,
    0x01990002,
])

PLUGIN_NAME = {
    0x00640002: 'sine',
    0x00650002: 'silence',
    0x00660002: 'tone',
}

class AkBankSourceData(object):
    def __init__(self, nbnksrc, src_sid):
        self._build_base(nbnksrc, src_sid)
        self._build_media(nbnksrc)
        self._build_plugin()
        self._build_extension()
        # not done by default to minimize some node finding since this option is uncommon
        #self._load_lang()
        self._lang_name = ''
        self._subdir = ''


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
        self.is_plugin_silence = (plugin == _PLUGIN_SILENCE)

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
            lang_name = _LANGUAGE_IDS.get(lang_value)
        else: #set of hashed names
            # typical values but languages can be anything (redefined in project options)
            lang_name = _LANGUAGE_HASHNAMES.get(lang_value)
            if not lang_name: #try loaded names (ex. Xenoblade DE uses "en" and "jp")
                lang_name = nlangid.get_attr('hashname')

        if not lang_name:
            lang_name = "language-%s" % (lang_value)

        lang_short = _LANGUAGE_SHORTNAMES.get(lang_name, lang_name)
        if lang_short == 'sfx':
            lang_short = ''
        self._lang_name = lang_short

        if lang_name == 'SFX':
            subdir = ''
        else:
            subdir = "%s/" % (lang_name)
        self._subdir = subdir
        

class CAkFx(object):
    def __init__(self, node, plugin_id):
        self.duration = 1.0 * 1000.0 #TODO default?
        self.plugin_id = plugin_id
        self._build(node)

    def _build(self, node):
        if not node:
            return

        #FxBaseInitialValues
        # fxID (may exist in AkFXCustom, or external in older versions)
        # uSize
        # Ak*FXParams
        if self.plugin_id == _PLUGIN_SILENCE: #silence
            nparams = node.find1(name='AkFXSrcSilenceParams')
            ndur = nparams.find(name='fDuration')
            self.duration = ndur.value()  * 1000.0 #to ms for consistency
