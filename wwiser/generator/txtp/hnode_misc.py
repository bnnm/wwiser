# Misc helper nodes, for rendering

# common config from all nodes to pass around
class NodeConfig(object):
    def __init__(self):
        # loop_flag = 0 in Wwise means "full loop or use loop points of file has (if file is sfx)",
        # and 1 means "don't loop even if the file has loop points" (like xma/dsp)
        # (>N also means "loop N times", but sounds shouldn't use this, only groups)
        self.loop = None

        self.gain = 0 #combination of all wwise's volume stuff (though technically still volume)
        self.delay = 0

        # marks
        self.crossfaded = False #RTPC/statechunks controlled silence
        self.silenced = False #low volume 
        self.silenced_default = False #default silence (without applying RTPC/statechunks)

        self.playevent = False
        self.rules = None
        self.duration = None
        self.entry = None
        self.exit = None

# common audio object with config
class NodeSound(object):
    def __init__(self):
        self.source = None #original source info (may not exist for silence)
        self.nsrc = None #to get root bank
        self.silent = False
        self.automations = None
        self.unreachable = False

        #clips can be modded by the engine (regular sounds are pre-changed when saved to .wem)
        self.clip = False
        self.fpa = 0  #moves track from start (>0=right, <0=left)
        self.fbt = 0  #mods beginning (>0=trim, <0=add begin repeat)
        self.fet = 0  #mods end (<0=trim, >0=add end repeat)
        self.fsd = 0  #original file duration (for calcs)
