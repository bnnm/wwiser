from ..registry import wgamesync, wstatechunks, wtransitions, wstingers, wgamevars, wparams
from . import wglobalsettings

# Simple container/simulation of internal wwise state, (currently set or newly registered paths).

class WwiseState(object):
    def __init__(self, txtpcache):
        self._txtpcache = txtpcache
        self.globalsettings = wglobalsettings.GlobalSettings()

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

        self._default_gspaths = None
        self._default_gsparams = None
        self._default_scpaths = None
        self._default_scparams = None
        self._default_gvpaths = None
        self._default_gvparams = None

        self.reset()

    def reset(self):
        # resets should make new lists and not just .clear() in case list is copied?
        self.reset_gs()
        self.reset_sc()
        self.reset_gv()
        self.transitions = wtransitions.Transitions()
        self.stingers = wstingers.Stingers()

    def reset_gs(self):
        self.gspaths = self._default_gspaths
        self.gsparams = self._default_gsparams
        if not self.gspaths:
            self.gspaths = wgamesync.GamesyncPaths(self._txtpcache)

    def reset_sc(self):
        self.scpaths = self._default_scpaths
        self.scparams = self._default_scparams
        if not self.scpaths:
            self.scpaths = wstatechunks.StateChunkPaths()

    def reset_gv(self):
        self.gvpaths = self._default_gvpaths
        self.gvparams = self._default_gvparams

    # ---

    def gs_registrable(self):
        return self.gsparams is None

    def get_gscombos(self):
        if self.gsparams or self.gspaths.is_empty():
            return None
        return self.gspaths.combos()

    def set_gs(self, gsparams):
        if self._default_gsparams:
            return
        self.gsparams = gsparams

    # ---

    def sc_registrable(self):
        return self.scparams is None

    def get_sccombos(self):
        if self.scparams or self.scpaths.is_empty():
            return None
        return self.scpaths.combos()

    def set_sc(self, scparams):
        self.scparams = scparams

    # ---

    def gv_registrable(self):
        return self.gvparams is not None

    def get_gvcombos(self):
        if self.gvparams or not self.gvpaths:
            return None
        return self.gvpaths.combos()

    def set_gv(self, gvparams):
        self.gvparams = gvparams

    # ---

    # Handle param defaults, that work mostly the same.
    #
    # Param list can be N combos of params, so make a default GS/SC/GV path handler, and pass the pre-parsed list
    # that is converted to internal stuff. To simplify 
    # If there is only one 1 path set it default to optimize calls (otherwise would try to get combos for 1 type).

    def set_gsdefaults(self, items):
        if items is None: #allow []
            return
        params = wparams.Params(allow_st=True, allow_sw=True)
        params.adds(items)

        gspaths = wgamesync.GamesyncPaths(self._txtpcache)
        gspaths.add_params(params)

        gscombos = gspaths.combos()
        if len(gscombos) == 1:
            self._default_gspaths = None
            self._default_gsparams = gscombos[0]
        elif len(gscombos) > 1:
            self._default_gspaths = gspaths
            self._default_gsparams = None

    def set_scdefaults(self, items):
        if items is None: #allow []
            return
        pass
        #self._default_sc = scparams
        #self.scparams = scparams

    def set_gvdefaults(self, items):
        if items is None: #allow []
            return
        params = wparams.Params(allow_gp=True)
        params.adds(items)

        gvpaths = wgamevars.GamevarsPaths()
        gvpaths.add_params(params)

        gvcombos = gvpaths.combos()
        if len(gvcombos) == 1:
            self._default_gvpaths = None
            self._default_gvparams = gvcombos[0]
        elif len(gvcombos) > 1:
            self._default_gvpaths = gvpaths
            self._default_gvparams = None
