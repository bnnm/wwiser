from ..registry import wgamesync, wstatechunks, wtransitions, wstingers

# simple container/simulation of internal wwise state, that is, currently set
# 
# It also serves as a way to register info

class WwiseState(object):
    def __init__(self, txtpcache):
        self._txtpcache = txtpcache
        self.reset()

    def reset(self):
        self.gspaths = wgamesync.GamesyncPaths(self._txtpcache)  #gamesync paths and config found during process
        self.gsparams = None  #current gamesync "path" config (default/empty means must find paths)

        #self.scpaths = wstatechunks.StateChunkPaths() #states used to change volume/mute tracks
        #self.scparams = None         # current volume combo in sub-txtp

        self.transitions = wtransitions.Transitions()
        self.stingers = wstingers.Stingers()
