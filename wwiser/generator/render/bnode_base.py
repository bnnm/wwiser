import logging
from . import bnode_misc, bnode_props, bnode_rtpc, bnode_source, bnode_transitions, bnode_tree
from ..txtp import wtxtp_info


#beware circular refs
#class CAkNode(object):
#    def __init__(self):
#       pass #no params since changing constructors is a pain

# common for all builder nodes (bnodes)
class CAkHircNode(object):
    def __init__(self):
        pass #no params since changing constructors is a pain

    def init_builder(self, builder):
        self._builder = builder

    def init_node(self, node):
        self._build_defaults(node)
        #todo limit to sound/action/etc, or manually call
        #self._build_references(node)
        #self._build_props(node) #xInitialParams
        #self._build_rtpcs(node)
        #self._build_states(node) #StateChunk
        #self._build_positioning(node)

        self.config = bnode_misc.NodeConfig()
        self.fields = wtxtp_info.TxtpFields() #main node fields, for printing
        self.stingers = []

        self._build(node)

    #--------------------------------------------------------------------------

    def _barf(self, text="not implemented"):
        raise ValueError("%s - %s %s" % (text, self.name, self.sid))


    def _build(self, node):
        self._barf()

    def _build_defaults(self, node):
        self.node = node
        self.name = node.get_name()
        self.nsid = node.find1(type='sid')
        self.sid = None
        if self.nsid:
            self.sid = self.nsid.value()

    def _build_references(self, node):
        
        # bus (BusInitialValues), sounds/musics (NodeBaseParams)
        nbusid = node.find1(name='OverrideBusId')
        if nbusid:
            self.busid = nbusid.value()
        
        # sounds/musics (NodeBaseParams)
        nparentid = node.find1(name='DirectParentID')
        if nparentid:
            self.parentid = nparentid.value()


    #--------------------------------------------------------------------------

    def __parse_props(self, ninit):
        props = bnode_props.CAkProps(ninit)

        if props.valid:
            self._builder.report_unknown_props(props.unknowns)

            self.config.volume = props.volume
            self.config.makeupgain = props.makeupgain
            self.config.pitch = props.pitch
            self.config.delay = props.delay
            self.config.idelay = props.idelay

            for nkey, nval in props.fields_std:
                self.fields.keyval(nkey, nval)

            for nkey, nmin, nmax in props.fields_rng:
                self.fields.keyminmax(nkey, nmin, nmax)

        return props.valid


    OLD_AUDIO_PROPS = [
        'Volume', 'Volume.min', 'Volume.max', 'LFE', 'LFE.min', 'LFE.max',
        'Pitch', 'Pitch.min', 'Pitch.max', 'LPF', 'LPF.min', 'LPF.max',
    ]
    OLD_ACTION_PROPS = [
        'tDelay', 'tDelayMin', 'tDelayMax', 'TTime', 'TTimeMin', 'TTimeMax',
    ]

    def _build_action_config(self, node):
        ninit = node.find1(name='ActionInitialValues') #used in action objects (CAkActionX)
        if not ninit:
            return

        ok = self.__parse_props(ninit)
        if ok:
            return

        #todo
        #may use PlayActionParams + eFadeCurve when TransitionTime is used to make a fade-in (goes after delay)

        #older
        for prop in self.OLD_ACTION_PROPS:
            nprop = ninit.find(name=prop)
            if not nprop:
                continue
            value = nprop.value()

            #fade-in curve
            #if value != 0 and (prop == 'TTime' or prop == 'TTimeMin'):
            #    self._barf("found " + prop)

            if value != 0 and (prop == 'tDelay' or prop == 'tDelayMin'):
                self.config.idelay = value

            if value != 0: #default to 0 if not set
                self.fields.prop(nprop)


    def _build_audio_config(self, node):
        name = node.get_name()

        # find songs that silence files to crossfade
        # mainly useful on Segment/Track level b/c usually games that set silence on
        # Switch/RanSeq do nothing interesting with it (ex. just to silence the whole song)
        check_state = name in ['CAkMusicTrack', 'CAkMusicSegment']
        check_rtpc = check_state
        nbase = node.find1(name='NodeBaseParams')
        if check_state and nbase:
            # state sets volume states to silence tracks (ex. MGR)
            # in rare cases those states are also used to slightly increase volume (Monster Hunter World's 3221323256.bnk)
            nstatechunk = nbase.find1(name='StateChunk')
            if nstatechunk:
                nstategroups = nstatechunk.finds(name='AkStateGroupChunk') #probably only one but...
                for nstategroup in nstategroups:
                    nstates = nstategroup.finds(name='AkState')
                    if not nstates: #possible to have groupchunks without pStates (ex Xcom2's 820279197)
                        continue

                    bank_id = nstategroup.get_root().get_id()
                    for nstate in nstates:
                        nstateinstanceid = nstate.find1(name='ulStateInstanceID')
                        if not nstateinstanceid: #???
                            continue
                        tid = nstateinstanceid.value()

                        # state should exist as a node and have a volume value (states for other stuff are common)
                        bstate = self._builder._get_bnode_by_ref(bank_id, tid, self.sid)
                        has_volumes = bstate and bstate.config.volume
                        if not has_volumes:
                            continue

                        self.config.crossfaded = True

                        logging.debug("generator: state volume found %s %s %s" % (self.sid, tid, node.get_name()))
                        nstategroupid = nstategroup.find1(name='ulStateGroupID') #parent group

                        nstateid = nstate.find1(name='ulStateID')
                        if nstategroupid and nstateid:
                            self.config.add_volume_state(nstategroupid, nstateid, bstate.config)
                            self.fields.keyvalvol(nstategroupid, nstateid, bstate.config.volume)

        if check_rtpc and nbase:
            # RTPC linked to volume (ex. DMC5 battle rank layers, ACB whispers)
            self._build_rtpc_config(nbase)

        # find other parameters
        ninit = node.find1(name='NodeInitialParams') #most objects that aren't actions nor states
        if not ninit:
            ninit = node.find1(name='StateInitialValues') #used in CAkState
        if not ninit:
            return

        ok = self.__parse_props(ninit)
        if ok:
            return

        #older
        for prop in self.OLD_AUDIO_PROPS:
            nprop = ninit.find(name=prop)
            if not nprop:
                continue
            value = nprop.value()
            if value != 0 and prop == 'Volume':
                self.config.volume = value #also min/max

            if value != 0: #default to 0 if not set
                self.fields.prop(nprop)

    def _build_rtpc_config(self, node):
        rtpcs = bnode_rtpc.AkRtpcList(node)
        if rtpcs.has_volume_rtpcs:
            self.config.rtpcs = rtpcs
            self.config.crossfaded = True
            for nid, minmax in rtpcs.fields:
                self.fields.rtpc(nid, minmax)
        return

    def _build_transition_rules(self, node, is_switch):
        rules = bnode_transitions.AkTransitionRules(node)
        for ntid in rules.ntrn:
            if ntid.value() == 0:
                continue
            if is_switch:
                self.ntransitions.append(ntid)
            else:
                # rare in playlists (Polyball, Spiderman)
                self._builder.report_transition_object()
        return

    def _build_tree(self, node):
        return bnode_tree.AkDecisionTree(node)

    def _build_stingers(self, node):
        nstingers = node.finds(name='CAkStinger')
        if not nstingers:
            return

        for nstinger in nstingers:
            stinger = bnode_misc.CAkStinger(nstinger)
            if stinger.tid:
                self.stingers.append(stinger)
        return

    def _build_silence(self, node, clip):
        sound = bnode_misc.NodeSound()
        sound.nsrc = node
        sound.silent = True
        sound.clip = clip
        return sound

    def _parse_source(self, nbnksrc):
        source = bnode_source.AkBankSource(nbnksrc, self.sid)

        if source.is_plugin_silence:
            nsize = nbnksrc.find(name='uSize')
            if nsize and nsize.value():
                # older games have inline plugin info
                source.plugin_fx = self._parse_sfx(nbnksrc, source.plugin_id)
            else:
                # newer games use another CAkFxCustom (though in theory could inline)
                bank_id = source.nsrc.get_root().get_id()
                tid = source.tid
                bfxcustom = self._builder._get_bnode_by_ref(bank_id, tid, self.sid)
                if bfxcustom:
                    source.plugin_fx = bfxcustom.fx

        return source

    def _parse_sfx(self, node, plugin_id):
        fx = bnode_source.NodeFx(node, plugin_id)
        return fx
