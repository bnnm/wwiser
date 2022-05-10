from . import wnode_misc, wnode_automation
from ..txtp import wtxtp_info

from .wrebuilder_base import CAkHircNode


#non-audio node, doesn't contribute to txtp
class _CAkNone(CAkHircNode):
    def __init__(self):
        super(_CAkNone, self).__init__()

    def _build(self, node):
        #ignore
        return

    def _make_txtp(self, txtp):
        #don't print node info in txtp
        return

    #def _process_txtp(self, txtp):
    #    return

# todo improve (stingers have no sid so it's set externally)
class _CAkStinger(CAkHircNode):
    def __init__(self):
        super(_CAkStinger, self).__init__()
        self.ntid = None #external

    def _build(self, node):
        #ignore
        return

    def _process_txtp(self, txtp):
        self._process_next(self.ntid, txtp)
        return

#non-audio node, but it's used as a reference
class _CAkState(CAkHircNode):
    def __init__(self):
        super(_CAkState, self).__init__()

    def _build(self, node):
        self._build_audio_config(node)
        #save config (used to check silences)
        return

    def _make_txtp(self, txtp):
        #don't print node info in txtp
        return

#plugin parameters, sometimes needed
class _CAkFxCustom(CAkHircNode):
    def __init__(self):
        super(_CAkFxCustom, self).__init__()
        self.fx = None

    def _build(self, node):
        #save config (used for sources)
        nfxid = node.find1(name='fxID')
        plugin_id = nfxid.value()

        self.fx = self._parse_sfx(node, plugin_id)
        return

    def _make_txtp(self, txtp):
        #don't print node info in txtp
        return

#******************************************************************************

class _CAkEvent(CAkHircNode):
    def __init__(self):
        super(_CAkEvent, self).__init__()
        self.ntids = None

    def _build(self, node):
        self.ntids = node.finds(name='ulActionID')
        return

    def _process_txtp(self, txtp):
        # N play actions are layered (may set a delay)
        txtp.group_layer(self.ntids, self.config)
        for ntid in self.ntids:
            self._process_next(ntid, txtp)
        txtp.group_done(self.ntids)
        return

#******************************************************************************

class _CAkDialogueEvent(CAkHircNode):
    def __init__(self):
        super(_CAkDialogueEvent, self).__init__()
        self.ntid = None
        self.tree = None

    def _build(self, node):
        self._build_audio_config(node)
        if self.config.loop is not None:
            self._barf("loop flag")

        tree = self._build_tree(node)
        if tree.init:
            self.tree = tree

    def _process_txtp(self, txtp):

        if self.ntid:
            # tree plays a single object with any state
            txtp.group_single(self.config)
            self._process_next(self.ntid, txtp)
            txtp.group_done()
            return

        if not self.tree:
            return 

        if not txtp.params:
            # find all possible gamesyncs paths (won't generate txtp)
            for path, ntid in self.tree.paths:
                unreachable = txtp.ppaths.adds(path)
                if not unreachable:
                    self._process_next(ntid, txtp)
                txtp.ppaths.done()
            return

        # find if current gamesync combo matches one of the paths
        npath_combo = self.tree.get_npath(txtp.params)
        if npath_combo:
            npath, ntid = npath_combo
            txtp.info.gamesyncs(npath)

            txtp.group_single(self.config)
            self._process_next(ntid, txtp)
            txtp.group_done()
        return

#******************************************************************************

class _CAkAction(CAkHircNode):
    def __init__(self):
        super(_CAkAction, self).__init__()
        self.ntid = None

    def _build(self, node):
        self._build_action_config(node)

        ntid = node.find(name='idExt')
        if not ntid: #older
            ntid = node.find(name='ulTargetID')
            #tDelay
            #tDelayMin
            #tDelayMax

        self.ntid = ntid

        self._build_subaction(node)

    def _build_subaction(self, node):
        return

#******************************************************************************

class _CAkActionPlayAndContinue(_CAkAction):
    def __init__(self):
        super(_CAkActionPlayAndContinue, self).__init__()

    def _build(self, node):
        self._barf()


#******************************************************************************

class _CAkActionTrigger(_CAkAction):
    def __init__(self):
        super(_CAkActionTrigger, self).__init__()

    def _process_txtp(self, txtp):
        # Trigger calls current music object (mranseq/mswitch usually) defined CAkStinger,
        # which in turn links to some segment and stops.
        # Trigger events may come before CAkStingers, and one trigger may call
        # stingers from any song (1 trigger > N stingers), so they are handled
        # separatedly during mranseq/mswitch.

        #logging.info("generator: trigger %i not implemented", self.sid)
        return

#******************************************************************************

class _CAkActionPlay(_CAkAction):
    def __init__(self):
        super(_CAkActionPlay, self).__init__()
        self.nbankid = None

    def _build_subaction(self, node):
        nparams = node.find1(name='PlayActionParams')
        if nparams:
            nbankid = node.find1(name='bankID')
            if not nbankid:
                nbankid = node.find1(name='fileID') #older
            # v26<= don't set bankID, automatically uses current
            self.nbankid = nbankid

    def _process_txtp(self, txtp):

        txtp.group_single(self.config) # rare but may contain config
        self._process_next(self.ntid, txtp, self.nbankid)
        txtp.group_done()
        return

#******************************************************************************

class _CAkActionPlayEvent(_CAkActionPlay): #_CAkActionPlay
    def __init__(self):
        super(_CAkActionPlayEvent, self).__init__()

#******************************************************************************

class _CAkSwitchCntr(CAkHircNode):
    def __init__(self):
        super(_CAkSwitchCntr, self).__init__()
        self.gtype = None
        self.ngname = None
        self.gvalue_ntids = {}

    def _build(self, node):
        self._build_audio_config(node)
        if self.config.loop is not None:
            self._barf("loop flag")

        self.gtype = node.find(name='eGroupType').value()
        self.ngname = node.find(name='ulGroupID')
        #ulDefaultSwitch: not used since we create all combos (must point to a valid path, or 0=none)
        #bIsContinuousValidation: step/continuous mode?
        #ulNumSwitchParams: config for switches (ex. FadeOutTime/FadeInTime)
        #children: same as NodeList

        ngvalues = node.find(name='SwitchList').finds(name='ulSwitchID')
        for ngvalue in ngvalues:
            ntids = ngvalue.get_parent().find(name='NodeList').finds(type='tid')
            if not ntids: #may define an empty path
                continue
            gvalue = ngvalue.value()
            self.gvalue_ntids[gvalue] = (ntids, ngvalue)
        return

    def _process_txtp(self, txtp):
        gtype = self.gtype
        gname = self.ngname.value()

        if not txtp.params:
            # find all possible gamesyncs paths (won't generate txtp)
            for ntids, ngvalue in self.gvalue_ntids.values(): #order doesn't matter
                gvalue = ngvalue.value()
                unreachable = txtp.ppaths.add(gtype, gname, ngvalue.value())
                if not unreachable:
                    for ntid in ntids:
                        self._process_next(ntid, txtp)
                txtp.ppaths.done()
            return

        #get current gamesync
        gvalue = txtp.params.current(gtype, gname)
        if gvalue is None:
            return
        if not gvalue in self.gvalue_ntids: #exact match (no * like MusicSwitches)
            return
        ntids, ngvalue = self.gvalue_ntids[gvalue]


        txtp.info.gamesync(gtype, self.ngname, ngvalue)
        txtp.group_layer(ntids, self.config)
        for ntid in ntids: #multi IDs are possible but rare (KOF13)
            self._process_next(ntid, txtp)
        txtp.group_done()
        return

#******************************************************************************

class _CAkRanSeqCntr(CAkHircNode):
    def __init__(self):
        super(_CAkRanSeqCntr, self).__init__()
        self.ntids = []

    def _build(self, node):
        self._build_audio_config(node)
        if self.config.loop is not None:
            self._barf("loop flag")

        #bIsGlobal: this object is a global entity (not needed, affects sequences/shuffles/etc)
        nmode = node.find(name='eMode')  #0=random / 1=sequence
        nrandom = node.find(name='eRandomMode')  #0=normal (repeatable), 1=shuffle (no repeatable)
        nloop = node.find(name='sLoopCount')  #1=once, 0=infinite, >1=N times
        ncontinuous = node.find(name='bIsContinuous')  #play one of the objects each time this is played, else play all
        navoidrepeat = node.find(name='wAvoidRepeatCount')  #excludes last played object from available list until N are played

        self.mode = nmode.value()
        self.random = nrandom.value()
        self.config.loop = nloop.value()
        self.continuous = ncontinuous.value()
        self.avoidrepeat = navoidrepeat.value()

        #sLoopModMin/sLoopModMax: random loop modifiers (loop -min +max)

        #eTransitionMode: defines a transition type between objects (ex. "delay" + fTransitionTime)
        #fTransitionTime / fTransitionTimeModMin / fTransitionTimeModMax: values for transition (depending on mode)
        #ntmode = node.find(name='eTransitionMode')
        #if ntmode and ntmode.value() != 0:
        #    self._barf("ranseq transition")


        # try playlist or children (both can be empty)
        nitems = node.finds(name='AkPlaylistItem')
        if nitems:
            # playlist items should have proper order (important in sequence types)
            for nitem in nitems:
                self.ntids.append( nitem.find(type='tid') )
                #self.nweights.append( nitem.find(name='weight') )
        else:
            # in rare cases playlist is empty, seen with "sequence" types though children aren't ordered (Borderlands 3)
            self.ntids = node.find(name='Children').finds(type='tid') 
            
        #if   self.mode == 0: #random
            #wAvoidRepeatCount: N objects must be played before one is repeated (also depends on normal/shuffle)
            #_bIsUsingWeight: unused? (AkPlaylistItem always has weight)

        #elif self.mode == 1: #sequence
            #bResetPlayListAtEachPlay: resets from 1st object each time is event replayed (in continuous mode)
            #bIsRestartBackward: once done, play item from last to first


        #ignored by Wwise but sometimes set, simplify
        if self.config.loop == 0 and not self.continuous:
            #if not self.avoidrepeat:
            #    self._barf("unknown loop mode in ranseq seq step")
            self.config.loop = None

        self.fields.props([nmode, nrandom, nloop, ncontinuous, navoidrepeat])
        return

    def _process_txtp(self, txtp):

        if   self.mode == 0 and self.continuous: #random + continuous (plays all objects randomly, on loop/next call restarts)
            txtp.group_random_continuous(self.ntids, self.config)

        elif self.mode == 0: #random + step (plays one object at random, on next call plays another object / cannot loop)
            txtp.group_random_step(self.ntids, self.config)

        elif self.mode == 1 and self.continuous: #sequence + continuous (plays all objects in sequence, on loop/next call restarts)
            txtp.group_sequence_continuous(self.ntids, self.config)

        elif self.mode == 1: #sequence + step (plays one object from first, on next call plays next object / cannot loop)
            txtp.group_sequence_step(self.ntids, self.config)

        else:
            self._barf('unknown ranseq mode')

        for ntid in self.ntids:
            self._process_next(ntid, txtp)
        txtp.group_done(self.ntids)

        return

#******************************************************************************

class _CAkLayerCntr(CAkHircNode):
    def __init__(self):
        super(_CAkLayerCntr, self).__init__()
        self.ntids = []

    def _build(self, node):
        self._build_audio_config(node)
        if self.config.loop is not None:
            self._barf("loop flag")

        nmode = node.find(name='bIsContinuousValidation')

        #if nmode: #newer only
        #if   mode == 0: #step (plays all at the same time, may loop or stop once all done)
        #elif mode == 1: #continuous (keeps playing nodes in RTPC region)

        self.ntids = node.find(name='Children').finds(type='tid')

        # usually found with RTPCs (ex. RPMs) + pLayers that define when layers are played
        nlayers = node.find1(name='pLayers')
        if nlayers:
            # RTPC linked to volume (ex. AC2 bgm+crowds)
            self._build_rtpc_config(nlayers)

        if nmode:
            self.fields.prop(nmode)
        return

    def _process_txtp(self, txtp):
        txtp.group_layer(self.ntids, self.config)
        for ntid in self.ntids:
            self._process_next(ntid, txtp)
        txtp.group_done(self.ntids)
        return

#******************************************************************************

class _CAkSound(CAkHircNode):
    def __init__(self):
        super(_CAkSound, self).__init__()
        self.sound = wnode_misc.NodeSound()

    def _build(self, node):
        self._build_audio_config(node)

        nloop = node.find(name='Loop')
        if nloop: #older
            self.config.loop = nloop.value()
            self.fields.prop(nloop)
            #there is min/max too

        nitem = node.find(name='AkBankSourceData')
        source = self._parse_source(nitem)
        self.sound.source = source
        self.sound.nsrc = source.nfileid

        self.fields.prop(source.nstreamtype)
        if source.nsourceid != source.nfileid:
            self.fields.prop(source.nfileid)
        return

    def _process_txtp(self, txtp):
        txtp.info.source(self.sound.nsrc, self.sound.source)
        txtp.source_sound(self.sound, self.config)
        return

#******************************************************************************

class _CAkMusicSwitchCntr(CAkHircNode):
    def __init__(self):
        super(_CAkMusicSwitchCntr, self).__init__()
        self.gtype = None
        self.ngname = None
        self.gvalue_ntid = {}
        self.has_tree = None
        self.ntid = False
        self.ntransitions = []
        self.tree = None

    def _build(self, node):
        self._build_audio_config(node)
        self._build_transition_rules(node, True)
        self._build_stingers(node)

        #Children: list, also in nodes
        #bIsContinuePlayback: ?
        #uMode: 0=BestMatch/1=Weighted

        tree = self._build_tree(node)
        if tree.init:
            #later versions use a tree
            self.tree = tree

        else:
            #earlier versions work like a normal switch
            self.has_tree = False

            self.gtype = node.find(name='eGroupType').value()
            self.ngname = node.find(name='ulGroupID')
            #ulDefaultSwitch: not needed since we create all combos

            nswitches = node.find(name='pAssocs')
            ngvalues = nswitches.finds(name='switchID')
            for ngvalue in ngvalues:
                ntid = ngvalue.get_parent().find(name='nodeID')
                #if not ntid: #may define empty path?
                #    continue
                gvalue = ngvalue.value()
                self.gvalue_ntid[gvalue] = (ntid, ngvalue)

    def _process_txtp(self, txtp):
        self._register_transitions(txtp)

        if self.ntid:
            # rarely tree plays a single object with any state
            txtp.group_single(self.config)
            self._process_next(self.ntid, txtp)
            txtp.group_done()
            return

        if self.tree:

            if not txtp.params:
                # find all possible gamesyncs paths (won't generate txtp)
                txtp.ppaths.add_stingers(self.stingers)

                for path, ntid in self.tree.paths:
                    unreachable = txtp.ppaths.adds(path)
                    if not unreachable:
                        self._process_next(ntid, txtp)
                    txtp.ppaths.done()
                return

            # find if current gamesync combo matches one of the paths
            npath_combo = self.tree.get_npath(txtp.params)
            if npath_combo:
                npath, ntid = npath_combo
                txtp.info.gamesyncs(npath)

                txtp.group_single(self.config) #rarely may contain volumes
                self._process_next(ntid, txtp)
                txtp.group_done()
            return

        else:
            gtype = self.gtype
            gname = self.ngname.value()

            if not txtp.params:
                # find all possible gamesyncs paths (won't generate txtp)
                for ntid, ngvalue in self.gvalue_ntid.values(): #order doesn't matter
                    gvalue = ngvalue.value()
                    unreachable = txtp.ppaths.add(gtype, gname, ngvalue.value())
                    if not unreachable:
                        self._process_next(ntid, txtp)
                    txtp.ppaths.done()
                return

            # get current gamesync
            gvalue = txtp.params.current(gtype, gname)
            if gvalue is None:
                return
            if not gvalue in self.gvalue_ntid:
                return
            ntid, ngvalue = self.gvalue_ntid[gvalue]
            txtp.info.gamesync(gtype, self.ngname, ngvalue)

            txtp.group_single(self.config)
            self._process_next(ntid, txtp)
            txtp.group_done()
            return

        return

#******************************************************************************

class _CAkMusicRanSeqCntr(CAkHircNode):
    def __init__(self):
        super(_CAkMusicRanSeqCntr, self).__init__()
        self.items = []
        self.ntransitions = []

    def _build(self, node):
        self._build_audio_config(node)
        if self.config.loop is not None:
            self._barf("loop flag")

        self._build_transition_rules(node, False)
        self._build_stingers(node)

        #playlists are "groups" that include 'leaf' objects or other groups
        # ex. item: playlist (sequence)
        #       item: segment A
        #       item: segment B
        #       item: playlist (random)
        #         item: segment C
        #         item: segment D
        # may play on loop: ABC ABC ABD ABC ABD ... (each group has its own loop config)
        nplaylist = node.find1(name='pPlayList')
        self._playlist(node, nplaylist, self.items)

    def _playlist(self, node, nplaylist, items):
        nitems = nplaylist.get_children()
        if not nitems:
            return

        for nitem in nitems:
            ntype = nitem.find1(name='eRSType')
            if not ntype: #older don't
                nchildren = nitem.find1(name='NumChildren')
                if nchildren and nchildren.value() == 0:
                    type = -1 #node
                else:
                    self._barf("unknown playlist type (old version?)")
            else:
                type = ntype.value()

            nloop = nitem.find1(name='Loop')

            #wAvoidRepeatCount
            #bIsUsingWeight
            #bIsShuffle
            nsubplaylist = nitem.find1(name='pPlayList')

            ntid = None
            if type == -1 or not nsubplaylist or nsubplaylist and not nsubplaylist.get_children():
                ntid = nitem.find(name='SegmentID') #0 on non-leaf nodes

            item = _CAkMusicRanSeqCntr_Item()
            item.nitem = nitem
            item.ntid = ntid
            item.type = type
            item.config.loop = nloop.value()
            item.fields.props([ntype, nloop])
             
            items.append(item)

            self._playlist(node, nsubplaylist, item.items)
        return

    def _process_txtp(self, txtp):
        self._register_transitions(txtp)

        if not txtp.params:
            txtp.ppaths.add_stingers(self.stingers)

        txtp.group_single(self.config) #typically useless but may have volumes
        self._process_playlist(txtp, self.items)
        txtp.group_done()

    def _process_playlist(self, txtp, items):
        if not items:
            return

        for item in items:
            type = item.type
            subitems = item.items

            txtp.info.next(item.nitem, item.fields)
            #leaf node uses -1 in newer versions, sid in older (ex. Enslaved)
            if type == -1 or item.ntid:
                transition = wnode_misc.NodeTransition()
                transition.play_before = False

                txtp.group_single(item.config, transition=transition)
                self._process_next(item.ntid, txtp)
                txtp.group_done()
            else:
                if   type == 0: #0: ContinuousSequence (plays all objects in sequence, on loop/next call restarts)
                    txtp.group_sequence_continuous(subitems, item.config)

                elif type == 1: #1: StepSequence (plays one object from first, on loop/next call plays next object)
                    txtp.group_sequence_step(subitems, item.config)

                elif type == 2: #2: ContinuousRandom (plays all objects randomly, on loop/next call restarts)
                    txtp.group_random_continuous(subitems, item.config)

                elif type == 3: #3: StepRandom (plays one object at random, on loop/next call plays another object)
                    txtp.group_random_step(subitems, item.config)

                else:
                    self._barf('unknown type')

                self._process_playlist(txtp, item.items)
                txtp.group_done(subitems)
            txtp.info.done()

        return


class _CAkMusicRanSeqCntr_Item():
    def __init__(self):
        self.nitem = None
        self.ntid = None
        self.type = None
        self.config = wnode_misc.NodeConfig()
        self.fields = wtxtp_info.TxtpFields()
        self.items = []


#******************************************************************************

class _CAkMusicSegment(CAkHircNode):
    def __init__(self):
        super(_CAkMusicSegment, self).__init__()
        self.ntids = []
        self.sound = None
        self.sconfig = None

    def _build(self, node):
        self._build_audio_config(node)
        if self.config.loop is not None:
            self._barf("loop flag")

        #AkMeterInfo: for switches
        nfdur = node.find(name='fDuration')
        self.config.duration = nfdur.value()
        self.fields.prop(nfdur)

        nmarkers = node.find(name='pArrayMarkers')
        if nmarkers:
            #we want "entry" and "exit" markers (fixed IDs), but are ordered in time (may go in any position)
            nmid1 = nmarkers.find1(value=43573010)
            nmid2 = nmarkers.find1(value=1539036744)
            if not nmid1 or not nmid2:
                # older versions (v62<=) use IDs 0/1 for entry/exit (other cues do use tids)
                nmid1 = nmarkers.find1(value=0)
                nmid2 = nmarkers.find1(value=1)

            if not nmid1 or not nmid2:
                self._barf("entry/exit markers not found")

            nmarker1 = nmid1.get_parent()
            nmarker2 = nmid2.get_parent()

            nmpos1 = nmarker1.find(name='fPosition')
            nmpos2 = nmarker2.find(name='fPosition')

            self.config.entry = nmpos1.value()
            self.config.exit = nmpos2.value()

            self.fields.keyval(nmarker1, nmpos1)
            self.fields.keyval(nmarker2, nmpos2)
            #self.fields.prop(nm2.get_parent())
        else:
            self._barf('markers not found')


        self.ntids = node.find(name='Children').finds(type='tid')
        # empty segments are allowed as silence
        if not self.ntids:
            self.sound = self._build_silence(self.node, True)
            self.sconfig = wnode_misc.NodeConfig()
        return

    def _process_txtp(self, txtp):
        # empty segments are allowed as silence
        if not self.ntids:
            #logging.info("generator: found empty segment %s" % (self.sid))
            elems = [self.sound]
            txtp.group_layer(elems, self.config)
            txtp.source_sound(self.sound, self.sconfig)
            txtp.group_done(elems)
            return

        txtp.group_layer(self.ntids, self.config)
        for ntid in self.ntids:
            self._process_next(ntid, txtp)
        txtp.group_done(self.ntids)
        return


#******************************************************************************

class _CAkMusicTrack(CAkHircNode):
    def __init__(self):
        super(_CAkMusicTrack, self).__init__()
        self.type = None
        self.subtracks = []
        self.gtype = None
        self.ngname = None
        self.gvalue_index = {}
        self.automations = {}

    def _build(self, node):
        self._build_audio_config(node)

        nloop = node.find(name='Loop')
        if nloop: #older
            self.config.loop = nloop.value()
            self.fields.prop(nloop)
            #there is min/max too

        # loops in MusicTracks are meaningless, ignore to avoid confusing the parser
        self.config.loop = None

        # prepare for clips
        self.automations = wnode_automation.AkClipAutomationList(node)

        ntype = node.find(name='eTrackType')
        if not ntype:
            ntype = node.find(name='eRSType')
        self.type = ntype.value()

        #save info about sources for later
        streaminfos = {}
        nitems = node.find1(name='pSource').finds(name='AkBankSourceData')
        for nitem in nitems:
            source = self._parse_source(nitem)
            tid = source.nsourceid.value()
            streaminfos[tid] = source

        #each track contains "clips" (srcs):
        #- 0: silent track (ex. Astral Chain 517843579)
        #- 1: normal
        #- N: layered with fades if overlapped (pre-defined)
        #Final length size depends on segment
        ncount = node.find1(name='numSubTrack')
        if not ncount: #empty / no clips
            return

        self.subtracks = [None] * ncount.value()

        #map clips to subtracks
        index = 0
        nsrcs = node.finds(name='AkTrackSrcInfo')
        for nsrc in nsrcs:
            track = nsrc.find(name='trackID').value()
            if not self.subtracks[track]:
                self.subtracks[track] = []

            clip = self._build_clip(streaminfos, nsrc)
            clip.sound.automations = self.automations.get(index)

            self.subtracks[track].append(clip)
            index += 1

        #pre-parse switch variables
        if self.type == 3:
            #TransParams: define switch transition
            nswitches = node.find(name='SwitchParams')
            self.gtype = nswitches.find(name='eGroupType').value()
            self.ngname = nswitches.find(name='uGroupID')
            ngvdefault = nswitches.find(name='uDefaultSwitch')
            self.gvalue_index = {}

            ngvalues = nswitches.finds(name='ulSwitchAssoc')
            for ngvalue in ngvalues: #switch N = track N
                gvalue = ngvalue.value()
                index = ngvalue.get_parent().get_index()
                self.gvalue_index[gvalue] = (index, ngvalue)

            # NMH3 uses default to play no subtrack (base) + one ulSwitchAssoc to play subtrack (base+extra)
            # maybe should also add "value none"
            gvdefault = ngvdefault.value()
            if gvdefault not in self.gvalue_index:
                 self.gvalue_index[gvdefault] = (None, ngvdefault) #None to force "don't play any subtrack"

            # maybe should include "any other state"?
            #self.gvalue_index[None] = (None, 0) #None to force "don't play any subtrack"

        self.fields.props([ntype, ncount])
        return

    def _build_clip(self, streaminfos, nsrc):
        nfpa = nsrc.find(name='fPlayAt')
        nfbt = nsrc.find(name='fBeginTrimOffset')
        nfet = nsrc.find(name='fEndTrimOffset')
        nfsd = nsrc.find(name='fSrcDuration')
        nsourceid = nsrc.find(name='sourceID')
        neventid = nsrc.find(name='eventID') #later versions

        clip = _CAkMusicTrack_Clip()
        clip.nitem = nsrc
        clip.neid = neventid
        clip.fields.props([nsourceid, neventid, nfpa, nfbt, nfet, nfsd])

        clip.sound.fpa = nfpa.value()
        clip.sound.fbt = nfbt.value()
        clip.sound.fet = nfet.value()
        clip.sound.fsd = nfsd.value()

        sourceid = nsourceid.value()
        if sourceid: #otherwise has eventid
            source = streaminfos[sourceid]

            clip.sound.source = source
            clip.sound.nsrc = source.nsourceid

            clip.fields.prop(source.nstreamtype)
            if source.nsourceid != source.nfileid:
                clip.fields.prop(source.nfileid)

        return clip

    def _process_txtp(self, txtp):
        if not self.subtracks: #empty / no clips
            return

        # node defines states that muted sources
        if self.config.volume_states:
            txtp.vpaths.add_nstates(self.config.volume_states)

        # musictrack can play in various ways
        if   self.type == 0: #normal (plays one subtrack, N aren't allowed)
            if len(self.subtracks) > 1:
                raise ValueError("more than 1 track")
            txtp.group_single(self.config)
            for subtrack in self.subtracks:
                self._process_clips(subtrack, txtp)
            txtp.group_done()

        elif self.type == 1: #random (plays random subtrack, on next call plays another)
            txtp.group_random_step(self.subtracks, self.config)
            for subtrack in self.subtracks:
                self._process_clips(subtrack, txtp)
            txtp.group_done(self.subtracks)

        elif self.type == 2: #sequence (plays first subtrack, on next call plays next)
            txtp.group_sequence_step(self.subtracks, self.config)
            for subtrack in self.subtracks:
                self._process_clips(subtrack, txtp)
            txtp.group_done(self.subtracks)

        elif self.type == 3: #switch (plays one subtrack depending on variables)
            gtype = self.gtype
            gname = self.ngname.value()

            if not txtp.params:
                # find all possible gamesyncs paths (won't generate txtp)
                for __, ngvalue in self.gvalue_index.values(): #order doesn't matter
                    if not ngvalue:
                        gvalue = 0
                    else:
                        gvalue = ngvalue.value()
                    txtp.ppaths.add(gtype, gname, gvalue)
                    #no subnodes
                    txtp.ppaths.done()
                return

            #get current gamesync
            gvalue = txtp.params.current(gtype, gname)
            if gvalue is None:
                return
            if not gvalue in self.gvalue_index:
                return
            index, ngvalue = self.gvalue_index[gvalue]

            #play subtrack based on index (assumed to follow order as defined)
            txtp.info.gamesync(gtype, self.ngname, ngvalue)

            if index is None:
                return # no subtrack, after adding path to gamesync (NHM3)
            subtrack = self.subtracks[index]

            txtp.group_single(self.config)
            self._process_clips(subtrack, txtp)
            txtp.group_done()

        else:
            self._barf()

        return

    def _process_clips(self, subtrack, txtp):
        if not subtrack:
            #logging.info("generator: found empty subtrack %s" % (self.sid))
            # rarely may happen with default = no track = silence (NMH3)
            sound = self._build_silence(self.node, True)
            config = wnode_misc.NodeConfig()
            sconfig = wnode_misc.NodeConfig()
            elems = [sound]
            txtp.group_layer(elems, config)
            txtp.source_sound(sound, sconfig)
            txtp.group_done(elems)
            return

        config = wnode_misc.NodeConfig()
        txtp.group_layer(subtrack, config)
        for clip in subtrack:
            if clip.neid and clip.neid.value():
                econfig = wnode_misc.NodeConfig()
                econfig.idelay = clip.sound.fpa #uses FPA to start segment, should work ok

                txtp.group_single(econfig)
                self._process_next(clip.neid, txtp)
                txtp.group_done()
            else:
                sconfig = wnode_misc.NodeConfig()
                sound = clip.sound
                txtp.info.next(clip.nitem, clip.fields)
                txtp.info.source(clip.sound.nsrc, clip.sound.source)
                txtp.info.done()
                txtp.source_sound(clip.sound, sconfig)
        txtp.group_done(subtrack)
        return

class _CAkMusicTrack_Clip(CAkHircNode):
    def __init__(self):
        self.nitem = None
        self.ntid = None
        self.neid = None
        self.sound = wnode_misc.NodeSound()
        self.sound.clip = True
        self.fields = wtxtp_info.TxtpFields()
