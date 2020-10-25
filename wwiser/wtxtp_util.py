

# common config from all nodes to pass around
#
# loop_flag = 0 in Wwise means "full loop or use loop points of file has",
# and 1 means "don't loop even if the file has loop points" (like xma/dsp)
# (>N also means "loop N times", but sounds shouldn't use this, only groups)
class NodeConfig(object):
    def __init__(self):
        self.loop = None
        self.volume = None
        self.delay = None
        self.idelay = None
        #markers
        self.duration = None
        self.entry = None
        self.exit = None

#common audio object with config
class NodeSound(object):
    def __init__(self):
        self.source = None #original source info (may not exist for silence)
        self.nsrc = None #to get root bank
        self.silent = False

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

class NodeSource(object):
    def __init__(self, node):
        self.nsrc = node
        self.nplugin = node.find(name='ulPluginID')
        self.nstreamtype = node.find(name='StreamType')
        self.nsourceid = node.find(name='sourceID')
        self.nfileid = node.find(name='uFileID')
        self.nlang = node.find(name='bIsLanguageSpecific')
        #0=bnk (always), 1/2=prefetch<>stream (varies with version)
        self.internal = (self.nstreamtype.value() == 0)

        # in older games (<=112) fileID exists and can be different from sourceID
        # (happens when clipped trims are different)
        if not self.nfileid:
            self.nfileid = self.nsourceid
        else:
            #when fileID exist it means 2 things:
            #- bank ID for internals (could be useful to print errors?), sourceID is bank's media ID
            #- file ID for streams, sourceID is just an info ID
            if self.internal:
                self.nfileid = self.nsourceid
        self.tid = self.nfileid.value()

        self._plugin()
        self._extension()
        #self._subdir()

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
            self.plugin_id = "%08x" % (plugin) #maybe should pass params
        else:
            self.plugin_id = None

    # each source may use its own extension
    def _extension(self):
        if self.plugin_id:
            self.extension = None
            self.extension_alt = None
            return

        version = self.nsrc.get_root().get_version()
        if version >= CODEC_EXTENSION_NEW_VERSION:
            self.extension = CODEC_EXTENSION_NEW
        else:
            self.extension = CODEC_EXTENSIONS_OLD.get(self.plugin_codec)
            if not self.extension:
                raise ValueError("extension not found for old version codec %s (report)" % (self.plugin_codec))
        
        if   self.extension == 'ogg':
            self.extension_alt = 'logg'
        elif self.extension == 'wav':
            self.extension_alt = 'lwav'
        else:
            self.extension_alt = self.extension

    #returns language subdir or nothing if source doesn't depend on subdir
    # not done by default to minimize some node finding
    def subdir(self):
        subdir = ''
        if not self.nlang or self.nlang.value() == 0: #default = not lang
            return subdir

        nroot = self.nsrc.get_root()
        nlangid = nroot.find1(name='BankHeader').find1(name='dwLanguageID')
        version = nroot.get_version()

        if version <= 120: #set of values
            value = nlangid.get_attr('valuefmt')
            pos1 = value.find('[')
            pos2 = value.find(']')
            if pos1 and pos2:
                value = value[pos1+1:pos2]
            else:
                value = None

        else: #set of hashed names
            value = nlangid.get_attr('hashname')
            if not value:
                # a few common in case wwnames wasn't included (but languages can be anything)
                names = {
                    393239870: 'SFX',
                    550298558: 'English(UK)',
                    684519430: 'English(US)',
                    323458483: 'French(France)',
                    1024389618: 'French(Canada)',
                    2008704848: 'Japanese',
                }
                value = names.get(nlangid.value())

        if not value:
            value = "%s" % (nlangid.value())


        if value == 'SFX': #possible?
            subdir = ''
        else:
            subdir = "%s/" % (value)
        return subdir

