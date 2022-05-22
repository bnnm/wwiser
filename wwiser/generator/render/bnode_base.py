from . import bnode_automation, bnode_props, bnode_rtpc, bnode_rules, bnode_source, bnode_tree, bnode_stinger, bnode_statechunk
from ..txtp import wtxtp_info


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

        self.fields = wtxtp_info.TxtpFields() #main node fields, for printing

        # loaded during process, if object has them (different classes have more or less)
        self.props = None
        self.statechunk = None
        self.rtpclist = None
        self.stingerlist = None

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

        #TODO improve props (inherited from parents)
        for nfld in props.fields_fld:
            self.fields.prop(nfld)

        for nkey, nval in props.fields_std:
            self.fields.keyval(nkey, nval)

        for nkey, nmin, nmax in props.fields_rng:
            self.fields.keyminmax(nkey, nmin, nmax)

        return props

    def _make_statechunk(self, nbase):
        if not nbase:
            return None

        statechunk = bnode_statechunk.AkStateChunk(nbase, self._builder)
        if not statechunk.valid:
            return None

        #TODO improve props (inherited from parents)
        for bsi in statechunk.get_states():
            self.fields.keyvalprops(bsi.nstategroupid, bsi.nstatevalueid, bsi.bstate.props)

        return statechunk

    def _make_rtpclist(self, nbase):
        if not nbase:
            return None

        # RTPC linked to volume (ex. DMC5 battle rank layers, ACB whispers)
        rtpclist = bnode_rtpc.AkRtpcList(nbase)
        if not rtpclist.valid:
            return None

        #TODO improve props (inherited from parents)
        for brtpc in rtpclist.get_rtpcs():
            self.fields.rtpc(brtpc.nid, brtpc.minmax())
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

    def _make_automationlist(self, node):
         return bnode_automation.AkClipAutomationList(node)

    def _make_stingerlist(self, node):
        return bnode_stinger.CAkStingerList(node)

    def _make_source(self, nbnksrc):
        source = bnode_source.AkBankSourceData(nbnksrc, self.sid)

        if source.is_plugin_silence:
            if source.plugin_size:
                # older games have inline plugin info
                source.plugin_fx = self._make_sfx(nbnksrc, source.plugin_id)
            else:
                # newer games use another CAkFxCustom (though in theory could inline)
                bank_id = source.nsrc.get_root().get_id()
                tid = source.tid
                bfxcustom = self._builder._get_bnode(bank_id, tid, sid_info=self.sid)
                if bfxcustom:
                    source.plugin_fx = bfxcustom.fx

        return source

    def _make_sfx(self, node, plugin_id):
        return bnode_source.CAkFx(node, plugin_id)
