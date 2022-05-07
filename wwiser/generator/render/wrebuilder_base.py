import logging
from . import wnode_misc, wnode_source, wnode_rtpc
from ..gamesync import wgamesync
from ..txtp import wtxtp_info


# common for all 'rebuilt' nodes
class _NodeHelper(object):
    def __init__(self):
        pass #no params since changing constructors is a pain

    def init_builder(self, builder):
        self.builder = builder

    def init_node(self, node):
        #self.version = node.get_root().get_version()
        self.node = node
        self.name = node.get_name()
        self.nsid = node.find1(type='sid')
        self.sid = None
        if self.nsid:
            self.sid = self.nsid.value()

        self.config = wnode_misc.NodeConfig()
        self.fields = wtxtp_info.TxtpFields() #main node fields, for printing
        self.stingers = []

        self._build(node)

    #--------------------------------------------------------------------------

    def _barf(self, text="not implemented"):
        raise ValueError("%s - %s %s" % (text, self.name, self.sid))

    def _process_next(self, ntid, txtp, nbankid=None):
        tid = ntid.value()
        if tid == 0:
            #this is fairly common in switches, that may define all combos but some nodes don't point to anything
            return

        if nbankid:
            # play actions reference bank by id (plus may save bankname in STID)
            bank_id = nbankid.value()
        else:
            # try same bank as node
            bank_id = ntid.get_root().get_id()

        bnode = self.builder._get_bnode_by_ref(bank_id, tid, sid_info=self.sid, nbankid_info=nbankid)
        if not bnode:
            return

        # filter HIRC nodes (for example drop unwanted calls to layered ActionPlay)
        if self.builder._filter and self.builder._filter.active:
            generate = self.builder._filter.allow_inner(bnode.node, bnode.nsid)
            if not generate:
                return

        #logging.debug("next: %s %s > %s", self.node.get_name(), self.sid, tid)
        bnode._make_txtp(txtp)
        return

    #--------------------------------------------------------------------------

    # info when generating transitions
    def _register_transitions(self, txtp):
        for ntid in self.ntransitions:
            node = self.builder._get_transition_node(ntid)
            txtp.transitions.add(node)
        return

    #--------------------------------------------------------------------------

    def _build(self, node):
        self._barf()
        return


    WARN_PROPS = [
        #"[TrimInTime]", "[TrimOutTime]", #seen in CAkState (ex. DMC5)
        #"[FadeInCurve]", "[FadeOutCurve]", #seen in CAkState, used in StateChunks (ex. NSR)
        "[LoopStart]", "[LoopEnd]",
        "[FadeInTime]", "[FadeOutTime]", "[LoopCrossfadeDuration]",
        "[CrossfadeUpCurve]", "[CrossfadeDownCurve]",
        #"[MakeUpGain]", #seems to be used when "auto normalize" is on (ex. Magatsu Wahrheit, MK Home Circuit)
        #"[BusVolume]", #percent of max? (ex. DmC)
        #"[OutputBusVolume]"
    ]
    OLD_AUDIO_PROPS = [
        'Volume', 'Volume.min', 'Volume.max', 'LFE', 'LFE.min', 'LFE.max',
        'Pitch', 'Pitch.min', 'Pitch.max', 'LPF', 'LPF.min', 'LPF.max',
    ]
    OLD_ACTION_PROPS = [
        'tDelay', 'tDelayMin', 'tDelayMax', 'TTime', 'TTimeMin', 'TTimeMax',
    ]

    def _parse_props(self, ninit):
        nvalues = ninit.find(name='AkPropBundle<AkPropValue,unsigned char>')
        if not nvalues:
            nvalues = ninit.find(name='AkPropBundle<float,unsigned short>')
        if not nvalues:
            nvalues = ninit.find(name='AkPropBundle<float>')
        if nvalues: #newer
            nprops = nvalues.finds(name='AkPropBundle')
            for nprop in nprops:
                nkey = nprop.find(name='pID')
                nval = nprop.find(name='pValue')

                valuefmt = nkey.get_attr('valuefmt')
                value = nval.value()
                if any(prop in valuefmt for prop in self.WARN_PROPS):
                    #self._barf('found prop %s' % (valuefmt))
                    self.builder._unknown_props[valuefmt] = True

                elif "[Loop]" in valuefmt:
                    self.config.loop = value

                elif "[Volume]" in valuefmt:
                    self.config.volume = value

                elif "[MakeUpGain]" in valuefmt:
                    self.config.makeupgain = value

                elif "[Pitch]" in valuefmt:
                    self.config.pitch = value

                elif "[DelayTime]" in valuefmt:
                    self.config.delay = value

                elif "[InitialDelay]" in valuefmt:
                    self.config.idelay = value * 1000.0 #float in seconds to ms

                #missing useful effects:
                #TransitionTime: used in play events to fade-in event

                self.fields.keyval(nkey, nval)

        #todo ranged values
        nranges = ninit.find(name='AkPropBundle<RANGED_MODIFIERS<AkPropValue>>')
        if nranges: #newer
            nprops = nranges.finds(name='AkPropBundle')
            for nprop in nprops:
                nkey = nprop.find(name='pID')
                nmin = nprop.find(name='min')
                nmax = nprop.find(name='max')

                self.fields.keyminmax(nkey, nmin, nmax)

        return nvalues or nranges


    def _build_action_config(self, node):
        ninit = node.find1(name='ActionInitialValues')
        if not ninit:
            return

        ok = self._parse_props(ninit)
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

    def _build_rtpc_config(self, node):
        if not node:
            return
        nrtpcs = node.finds(name='RTPC')
        if not nrtpcs:
            return
        for nrtpc in nrtpcs:
            rtpc = wnode_rtpc.NodeRtpc(nrtpc)
            if not rtpc.is_volume:
                continue
            self.config.rtpcs.append(rtpc)
            self.config.crossfaded = True
            self.fields.rtpc(rtpc.nid, rtpc.minmax())

        return

    def _build_audio_config(self, node):
        name = node.get_name()

        # find songs that silence files to crossfade
        # mainly useful on Segment/Track level b/c usually games that set silence on
        # Switch/RanSeq do nothing interesting with it (ex. just to silence the whole song)
        check_state = name in ['CAkMusicTrack', 'CAkMusicSegment']
        check_rtpc = check_state
        nbase = node.find1(name='NodeBaseParams')
        if nbase and check_state:
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
                        bstate = self.builder._get_bnode_by_ref(bank_id, tid, self.sid)
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

        if nbase and check_rtpc:
            # RTPC linked to volume (ex. DMC5 battle rank layers, ACB whispers)
            self._build_rtpc_config(nbase)

        # find other parameters
        ninit = node.find1(name='NodeInitialParams')
        if not ninit:
            ninit = node.find1(name='StateInitialValues')
        if not ninit:
            return

        ok = self._parse_props(ninit)
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

    def _build_transitions(self, node, is_switch):
        #AkMeterInfo: into for transitions
        #pRules > AkMusicTransitionRule: when gamesync changes from one node to other (with fades or transition nodes)
        #- srcID/dstID: source/destination node, id=object, -1=any, 0=nothing
        #- other values: how to sync (like change when reaching node's "ExitMarker" cue)
        #  (may only be used if transitionTime > 0?)
        # * AkMusicTransitionObject: print

        nmtos = node.finds(name='AkMusicTransitionObject')
        # older versions use bIsTransObjectEnabled to signal use, but segmentID is 0 if false anyway
        for nmto in nmtos:
            ntid = nmto.find1(name='segmentID')
            if ntid and ntid.value() != 0:
                if is_switch:
                    self.ntransitions.append(ntid)
                else:
                    # rare in playlists (Polyball, Spiderman)
                    self.builder.report_transition_object()

        return

    def _build_stingers(self, node):
        nstingers = node.finds(name='CAkStinger')
        if not nstingers:
            return

        for nstinger in nstingers:
            stinger = wnode_misc.NodeStinger()
            stinger.node = nstinger
            stinger.ntrigger = nstinger.find1(name='TriggerID') #idExt called from trigger action
            stinger.ntid = nstinger.find1(name='SegmentID') #segment to play (may be 0)
            if stinger.ntid and stinger.ntid.value() != 0:
                self.stingers.append(stinger)
        return

    def _build_silence(self, node, clip):
        sound = wnode_misc.NodeSound()
        sound.nsrc = node
        sound.silent = True
        sound.clip = clip
        return sound

    def _parse_source(self, nbnksrc):
        source = wnode_source.NodeSource(nbnksrc, self.sid)

        if source.plugin_id == 0x00650002: #silence
            nsize = nbnksrc.find(name='uSize')
            if nsize and nsize.value():
                # older games have inline plugin info
                source.plugin_fx = self._parse_sfx(nbnksrc, source.plugin_id)
            else:
                # newer games use another CAkFxCustom (though in theory could inline)
                bank_id = source.nsrc.get_root().get_id()
                tid = source.tid
                bfxcustom = self.builder._get_bnode_by_ref(bank_id, tid, self.sid)
                if bfxcustom:
                    source.plugin_fx = bfxcustom.fx

        return source

    def _parse_sfx(self, node, plugin_id):
        fx = wnode_misc.NodeFx(node, plugin_id)
        return fx

    #--------------------------------------------------------------------------

    #tree with multi gamesync (order of gamesyncs is branch order in tree)
    def _build_tree(self, node, ntree):
        self.args = []
        self.paths = []
        self.tree = {}

        # tree's args (gamesync key) are given in Arguments, and possible values in AkDecisionTree, that contains
        # 'pNodes' with 'Node', that have keys (gamesync value) and children or audioNodeId:
        #   Arguments
        #       bgm
        #           scene
        #
        #   AkDecisionTree
        #       key=*
        #           key=bgm001
        #               key=scene001
        #                   audioNodeId=123456789
        #           key=*
        #               key=*
        #                   audioNodeId=234567890
        #
        # Thus: (-=*, bgm=bgm001, scene=scene001 > 123456789) or (-=*, bgm=*, scene=* > 234567890).
        # Paths must be unique (can't point to different IDs).
        #
        # Wwise picks paths depending on mode:
        # - "best match": (default) selects "paths with least amount of wildcards" (meaning favors matching values)
        # - "weighted": random based on based on "weight" (0=never, 100=always)
        # For example:
        # (bgm=bgm001, scene=*, subscene=001) vs (bgm=*, scene=scene001, subscene=*) picks the later (less *)
        #
        # This behaves like "best match", but saves GS values as "*" (that shouldn't be possible)
        #
        # Trees always start with a implicit "*" key that matches anything, so it's possible
        # to have trees with no arguments that point to an audioNodeId = non-switch tree

        # args has gamesync type+names, and tree "key" is value (where 0=any)
        depth = node.find1(name='uTreeDepth').value()
        nargs = node.finds(name='AkGameSync')
        if depth != len(nargs): #not possible?
            self._barf(text="tree depth and args don't match")

        self.args = []
        for narg in nargs:
            ngtype = narg.find(name='eGroupType')
            ngname = narg.find(name='ulGroup')
            if ngtype:
                gtype = ngtype.value()
            else: #DialogueEvent in older versions, assumed default
                gtype = wgamesync.TYPE_STATE
            self.args.append( (gtype, ngname) )

        # make a tree for access, plus a path list (similar to how the editor shows them) for GS combos
        # - [val1] = {
        #       [*] = { 12345 },
        #       [val2] = {
        #           [val3] = { ... }
        #       }
        #   }
        # - [(gtype1, ngname1, ngvalue1), (gtype2, ngname2, ngvalue2), ...] > ntid (xN)
        gamesyncs = [None] * len(nargs) #temp list

        nnodes = ntree.find1(name='pNodes') #always
        nnode = nnodes.find1(name='Node') #always
        npnodes = nnode.find1(name='pNodes') #may be empty
        if npnodes:
            self._build_tree_nodes(self.tree, 0, npnodes, gamesyncs)
        elif nnode:
            # In rare cases may only contain one node for key 0, no depth (NMH3). This can be added
            # as a "generic path" with no vars selected, meaning ignores vars and matches 1 object.
            self.ntid = nnode.find1(name='audioNodeId')


    def _build_tree_nodes(self, tree, depth, npnodes, gamesyncs):
        if depth >= len(self.args):
            self._barf(text="wrong depth") #shouldn't happen

        if not npnodes: #short branch?
            return
        nchildren = npnodes.get_children() #parser shouldn't make empty pnodes
        if not nchildren:
            return

        gtype, ngname = self.args[depth]

        for nnode in nchildren:
            ngvalue = nnode.find1(name='key')
            npnodes = nnode.find1(name='pNodes')
            gamesyncs[depth] = (gtype, ngname, ngvalue) #overwrite per node, will be copied

            key = ngvalue.value()

            if not npnodes: #depth + 1 == len(self.args): #not always correct
                ntid = nnode.find1(name='audioNodeId')
                tree[key] = (ngvalue, ntid, None)
                self._build_tree_leaf(ntid, ngvalue, gamesyncs)

            else:
                subtree = {}
                tree[key] = (ngvalue, None, subtree)
                self._build_tree_nodes(subtree, depth + 1, npnodes, gamesyncs)
        return

    def _build_tree_leaf(self, ntid, ngvalue, gamesyncs):
        # clone list of gamesyncs and final ntid (both lists as an optimization for huge trees)
        path = []
        for gamesync in gamesyncs:
            if gamesync is None: #smaller path, rare
                break
            gtype, ngname, ngvalue = gamesync
            path.append( (gtype, ngname.value(), ngvalue.value()) )
        self.paths.append( (path, ntid) )

        return

    def _tree_get_npath(self, txtp):
        # find gamesyncs matches in path

        # follow tree up to match, with implicit depth args
        npath = []
        curr_tree = self.tree
        for gtype, ngname in self.args:
            # current arg must be defined to some value
            gvalue = txtp.params.current(gtype, ngname.value())
            if gvalue is None: #not defined = can't match
                return None

            # value must exist in tree
            match = curr_tree.get(gvalue) # exact match (could match * too if gvalue is set to 0)
            if not match:
                match = curr_tree.get(0) # * match
            if not match:
                return None

            ngvalue, ntid, subtree = match
            npath.append( (gtype, ngname, ngvalue) )

            if not ntid:
                curr_tree = subtree # try next args = higher depth
            else:
                return (npath, ntid)

        return None


    #--------------------------------------------------------------------------

    def _make_txtp(self, txtp):
        try:
            txtp.info.next(self.node, self.fields, nsid=self.nsid)
            self._process_txtp(txtp)
            txtp.info.done()
        except Exception: #as e #autochained
            raise ValueError("Error processing TXTP for node %i" % (self.sid)) #from e

    def _process_txtp(self, txtp):
        self._barf("must implement")
