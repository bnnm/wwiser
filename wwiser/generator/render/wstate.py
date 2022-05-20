from ..registry import wgamesync, wstatechunks, wtransitions, wstingers

# simple container/simulation of internal wwise state, that is, currently set
# 
# It also serves as a way to register info

class WwiseState(object):
    def __init__(self, txtpcache):
        self._txtpcache = txtpcache

        # combos found during process
        self.gspaths = None #gamesyncs: states/switches for dynamic object paths
        self.scpaths = None #statechunks: states for dynamic property changes
        self.gvpaths = None #gamevars: variables for dynamic property changes

        # currently set values (when None renderer will try to find possible combos)
        self.gsparams = None
        self.scparams = None
        self.gvparams = None

        # special values, not reset
        self.transitions = None # sub-objects when changing from one GS path to other
        self.stingers = None # sub-objects triggered with another plays

        self._default_gs = None
        self._default_sc = None
        self._default_gv = None

        self.reset()

    def reset(self):
        # resets should make new lists and not just .clear() in case list is copied?
        self.reset_gs()
        self.reset_sc()
        self.reset_gv()
        self.transitions = wtransitions.Transitions()
        self.stingers = wstingers.Stingers()


    def reset_gs(self):
        self.gspaths = wgamesync.GamesyncPaths(self._txtpcache)  
        self.gsparams = self._default_gs

    def reset_sc(self):
        self.scpaths = wstatechunks.StateChunkPaths()  
        self.scparams = self._default_sc

    def reset_gv(self):
        self.gvpaths = None #?
        self.gvparams = self._default_gv

    # ---

    def has_gsset(self):
        return self.gsparams is not None

    def get_gscombos(self):
        if self.gsparams or self.gspaths.is_empty():
            return None
        return self.gspaths.combos()

    def set_gs(self, gsparams):
        if self._default_gs:
            return
        self.gsparams = gsparams

    def set_gsdefault(self, gsparams):
        self._default_gs = gsparams
        self.gsparams = gsparams

    # ---

    def has_scset(self):
        return self.scparams is not None

    def get_sccombos(self):
        if self.scparams or self.scpaths.is_empty():
            return None
        return self.scpaths.combos()

    def set_sc(self, scparams):
        self.scparams = scparams

    def set_scdefault(self, scparams):
        self._default_sc = scparams
        self.scparams = scparams

    # ---

    def has_gvset(self):
        return self.gvparams is not None

    def get_gvcombos(self):
        if self.gvparams: #or self.gvpaths.is_empty():
            return None
        return None #not self.gvpaths.is_empty()

    def set_gv(self, gvparams):
        self.gvparams = gvparams

    def set_gvdefault(self, gvparams):
        self._default_gv = gvparams
        self.gvparams = gvparams
