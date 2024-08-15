from . import bnode_automation, bnode_props, bnode_rtpc, bnode_rules, bnode_source, bnode_tree, bnode_stinger, bnode_statechunk, bnode_fxs, bnode_auxs
from ..txtp import wtxtp_fields


#beware circular refs
#class CAkNode(object):
#    def __init__(self):
#       pass #no params since changing constructors is a pain

# common for all builder nodes (bnodes)
class CAkHircNode(object):
    def __init__(self):
        pass #no params since inheriting and changing python constructors is a pain

    def init_builder(self, builder):
        self._builder = builder

    def init_node(self, node):
        self._build_defaults(node)

        self.fields = wtxtp_fields.TxtpFields() #main node fields, for printing

        # loaded during process, if object has them (different classes have more or less)
        self.props = None
        self.statechunk = None
        self.rtpclist = None
        self.stingerlist = None
        self.fxlist = None

        self.bbus = None
        self.bparent = None

        self._build(node)

    #--------------------------------------------------------------------------

    def _barf(self, text="not implemented"):
        raise ValueError("%s - %s %s" % (text, self.name, self.sid))


    def _build_defaults(self, node):
        # common to all HIRC nodes
        self.node = node
        self.name = node.get_name()
        self.nsid = node.find1(type='sid')
        self.sid = None
        if self.nsid:
            self.sid = self.nsid.value()

    def _build(self, node):
        self._barf()

    #--------------------------------------------------------------------------

    def _read_device(self, ntid):
        return self._builder._get_bnode_link_device(ntid)

    def _read_bus(self, ntid):
        return self._builder._get_bnode_link_bus(ntid)

    def _read_parent(self, ntid):
        return self._builder._get_bnode_link(ntid)

    def _make_props(self, nbase):
        if not nbase:
            return None
        props = bnode_props.CAkProps(nbase)
        if not props.valid:
            return None
        self._builder.report_unknown_props(props.unknowns)

        # add only behavior props (relative props include parents+buses, which aren't always part of path tree)
        self.fields.props(props.fields_bfld)
        self.fields.keyvals(props.fields_bstd)
        self.fields.keyminmaxs(props.fields_brng)

        return props

    def _make_statechunk(self, nbase):
        if not nbase:
            return None

        statechunk = bnode_statechunk.AkStateChunk(nbase, self._builder)
        if not statechunk.valid:
            return None

        # during during calculations to make a final list
        #for bsi in statechunk.get_states():
        #    self.fields.statechunk(bsi.nstategroupid, bsi.nstatevalueid, bsi.props)

        return statechunk

    def _make_rtpclist(self, nbase):
        if not nbase:
            return None

        # RTPC linked to volume (ex. DMC5 battle rank layers, ACB whispers)
        globalsettings = self._builder._globalsettings
        rtpclist = bnode_rtpc.AkRtpcList(nbase, globalsettings)
        if not rtpclist.valid:
            return None

        # during during calculations to make a final list
        #for brtpc in rtpclist.get_rtpcs():
        #    self.fields.rtpc(brtpc.nid, brtpc.nparam, brtpc.values_x(), brtpc.values_y())
        return rtpclist

    def _make_transition_rules(self, node, is_switch):
        rules = bnode_rules.AkTransitionRules(node)
        if not is_switch and rules.ntrns:
            # rare in playlists (Polyball, Spiderman)
            self._builder.report_transition_object()
        return rules

    def _make_tree(self, node):
        tree = bnode_tree.AkDecisionTree(node)
        if not tree.init:
            return None
        return tree

    def _make_fxlist(self, node):
        fxlist = bnode_fxs.AkFxChunkList(node, self._builder)
        if not fxlist.init:
            return None
        return fxlist

    def _make_auxlist(self, node, bparent):
        auxlist = bnode_auxs.AkAuxList(node, bparent, self)
        if not auxlist.init:
            return None
        return auxlist

    def _make_automationlist(self, node):
         return bnode_automation.AkClipAutomationList(node)

    def _make_stingerlist(self, node):
        return bnode_stinger.CAkStingerList(node)

    def _make_source(self, nbnksrc):
        source = bnode_source.AkBankSourceData(nbnksrc, self.sid)

        # sources may be:
        # - standard .wem
        # - Wwise Audio Input (audio capturing)
        # - Wwise Silence
        # - Wwise Sine (configurable secs, simple sine)
        # - Wwise Synth One (infinite duration, kind of midi-controlled sine?)
        # - Wwise Tone Generator (~1sec,  selectable tone like sine, triangle, noise, etc)
        # - Wwise External Source (handled separately)

        if source.is_plugin_silence:
            if source.plugin_size:
                # older games have inline plugin info
                source.plugin_fx = self._make_sfx(nbnksrc, source.plugin_id)
            else:
                # newer games use another CAkFxCustom (though in theory could inline)
                bank_id = source.nsrc.get_root().get_id()
                tid = source.tid
                bfxcustom = self._builder._get_bnode(bank_id, tid)
                if bfxcustom:
                    source.plugin_fx = bfxcustom.fx

        return source

    def _make_sfx(self, node, plugin_id):
        return bnode_source.CAkFx(node, plugin_id)
