import logging
from . import bnode_misc, bnode_props, bnode_rtpc, bnode_rules, bnode_source, bnode_tree, bnode_stinger, bnode_statechunk
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

        self.config = bnode_misc.NodeConfig()
        self.fields = wtxtp_info.TxtpFields() #main node fields, for printing

        # loaded during process, if object has them (different classes have more or less)
        self.nbusid = None
        self.nparentid = None
        self.props = None
        self.statechunk = None
        self.rtpclist = None
        self.stingerlist = None

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

    def _make_props(self, nbase):
        if not nbase:
            return None
        props = bnode_props.CAkProps(nbase)
        if not props.valid:
            return None
        self._builder.report_unknown_props(props.unknowns)

        self.config.volume = props.volume
        self.config.makeupgain = props.makeupgain
        self.config.pitch = props.pitch
        self.config.delay = props.delay
        self.config.idelay = props.idelay


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

        # find songs that silence files with states
        # mainly useful on MSegment/MTrack level b/c usually games that set silence on those,
        # while on MSwitch/MRanSeq are often just to silence the whole song.
        hircname = self.node.get_name()
        check_state = hircname in ['CAkMusicTrack', 'CAkMusicSegment']
        if check_state:
            bstates = statechunk.get_volume_states()
            self.config.crossfaded = len(bstates) != 0
            for bsi in bstates:
                self.config.add_volume_state(bsi.nstategroupid, bsi.nstatevalueid, bsi.bstate.config)
                self.fields.keyvalvol(bsi.nstategroupid, bsi.nstatevalueid, bsi.bstate.config.volume)

        return statechunk

    def _make_rtpclist(self, nbase):
        if not nbase:
            return None

        # RTPC linked to volume (ex. DMC5 battle rank layers, ACB whispers)
        rtpclist = bnode_rtpc.AkRtpcList(nbase)
        if not rtpclist.valid:
            return None

        # find songs that silence crossfade files with rtpcs
        # mainly useful on Segment/Track level b/c usually games that set silence on
        # Switch/RanSeq do nothing interesting with it (ex. just to silence the whole song)
        hircname = self.node.get_name()
        check_rtpc = hircname in ['CAkMusicTrack', 'CAkMusicSegment']
        if check_rtpc:
            brtpcs = rtpclist.get_volume_rtpcs()
            self.config.crossfaded = len(brtpcs) != 0
            self.config.rtpcs = brtpcs
            for brtpc in brtpcs:
                nid = brtpc.nid
                minmax = brtpc.minmax()
                self.fields.rtpc(nid, minmax)
        return rtpclist

    def _build_transition_rules(self, node, is_switch):
        self.rules = bnode_rules.AkTransitionRules(node)
        if not is_switch and self.rules.ntrns:
            # rare in playlists (Polyball, Spiderman)
            self._builder.report_transition_object()
        return

    def _build_tree(self, node):
        return bnode_tree.AkDecisionTree(node)

    def _build_stingers(self, node):
        self.stingerlist = bnode_stinger.CAkStingerList(node)
        return

    def _build_source(self, nbnksrc):
        source = bnode_source.AkBankSourceData(nbnksrc, self.sid)

        if source.is_plugin_silence:
            if source.plugin_size:
                # older games have inline plugin info
                source.plugin_fx = self._build_sfx(nbnksrc, source.plugin_id)
            else:
                # newer games use another CAkFxCustom (though in theory could inline)
                bank_id = source.nsrc.get_root().get_id()
                tid = source.tid
                bfxcustom = self._builder._get_bnode(bank_id, tid, sid_info=self.sid)
                if bfxcustom:
                    source.plugin_fx = bfxcustom.fx

        return source

    def _build_sfx(self, node, plugin_id):
        return bnode_source.CAkFx(node, plugin_id)

    #TODO
    def _build_silence(self, node, clip):
        sound = bnode_misc.NodeSound()
        sound.nsrc = node
        sound.silent = True
        sound.clip = clip
        return sound
