
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
        self.rtpcs = None
        #markers
        self.duration = None
        self.entry = None
        self.exit = None
        self.exit = None

        # states that when active silence group
        self.volume_states = []

    def add_volume_state(self, ngroup, nvalue, config):
        item = (ngroup, nvalue, config)
        self.volume_states.append(item)


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

class CAkStinger(object):
    def __init__(self, node):
        self.node = node
        self.ntrigger = None
        self.ntid = None
        self.tid = None
        self._build(node)

    def _build(self, node):
        self.ntrigger = node.find1(name='TriggerID') #idExt called from trigger action
        self.ntid = node.find1(name='SegmentID') #segment to play (may be 0)
        if self.ntid:
            self.tid = self.ntid.value()
