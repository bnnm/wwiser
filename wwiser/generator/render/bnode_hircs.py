import logging
from ..txtp import hnode_misc, wtxtp_fields

from .bnode_base import CAkHircNode
from .bnode_markers import AkMarkerList


#******************************************************************************
# MISC

#non-audio node, doesn't contribute to txtp
class CAkNone(CAkHircNode):
    def __init__(self):
        super(CAkNone, self).__init__()

    def _build(self, node):
        #ignore
        return

# non-audio node, but it's used as a reference in StateChunks
class CAkState(CAkHircNode):
    def __init__(self):
        super(CAkState, self).__init__()

    def _build(self, node):
        nbase = node.find1(name='StateInitialValues')

        self.props = self._make_props(nbase)
        return

# plugin parameters, sometimes needed (referenced in AkBankSourceData)
class CAkFxCustom(CAkHircNode):
    def __init__(self):
        super(CAkFxCustom, self).__init__()
        self.fx = None

    def _build(self, node):
        nbase = node.find1(name='FxBaseInitialValues')

        # save config (used for sources)
        nfxid = nbase.find1(name='fxID')
        plugin_id = nfxid.value()
        self.fx = self._make_sfx(node, plugin_id)

        self.statechunk = self._make_statechunk(nbase)
        self.rtpclist = self._make_rtpclist(nbase)

        return

# same as the above but common config (reused unlike CAkFxCustom)
class CAkFxShareSet(CAkFxCustom):
    def __init__(self):
        super(CAkFxShareSet, self).__init__()


# output config
class CAkBus(CAkHircNode):
    def __init__(self):
        super(CAkBus, self).__init__()
        self.bdevice = None
        self.auxlist = None

    def _build(self, node):
        nbase = node.find1(name='BusInitialValues')

        nbusid = nbase.find1(name='OverrideBusId')
        self.bparent = self._read_bus(nbusid) #parent bus of this bus

        # needed to check audio output? (only on later versions and if a parent bus)
        ndeviceid = nbase.find1(name='idDeviceShareset')
        self.bdevice = self._read_device(ndeviceid)

        # use to guess is non-output bus? (usually not set)
        #uChannelConfig

        self.props = self._make_props(nbase)
        #PositioningParams

        self.statechunk = self._make_statechunk(nbase)
        self.rtpclist = self._make_rtpclist(nbase)

        ninitfx = nbase.find1(name='BusInitialFxParams')
        self.fxlist = self._make_fxlist(ninitfx)

        # auxs aren't normally needed but in some cases devs do strange stuff with bus volumes
        nauxs = nbase.find1(name='AuxParams')
        self.auxlist = self._make_auxlist(nauxs, self.bparent)

        return

class CAkAuxBus(CAkBus):
    def __init__(self):
        super(CAkAuxBus, self).__init__()

    #  same but only used in AuxParams


class CAkAudioDevice(CAkHircNode):
    def __init__(self):
        super(CAkAudioDevice, self).__init__()
        self.silent = False

    def _build(self, node):
        #nbase = node.find1(name='AudioDeviceInitialValues') #only in 140>=
        nbase = node.find1(name='FxBaseInitialValues')
        nfxid = nbase.find1(name='fxID')

        fxid = nfxid.value()
        if fxid == 0x00B50007: #No Output
            self.silent = True

            # only used in latest versions and this just means there is no
            # output (txtp config could be marked 'silenced'), not sure when would be used though.
            # ex. MK1 Switch redirects output to "Critical_Health_Controller" while silencing main
            #self._barf("No_Output CAkAudioDevice, report")
            logging.info("WARNING: No_Output CAkAudioDevice found (report)")

        # Internally has InitialRTPC/StateChunk/PluginPropertyValue/FXList but doesn't
        # seem possible in editor, just that internally works like an FX plugin.
        # It does have an FX list

        return


#******************************************************************************
# EVENTS AND ACTIONS

class CAkEvent(CAkHircNode):
    def __init__(self):
        super(CAkEvent, self).__init__()
        self.ntids = None

    def _build(self, node):
        nbase = node.find1(name='EventInitialValues')

        self.ntids = nbase.finds(name='ulActionID')
        # events that don't call anything seem trimmed so this should exist

        # no other config
        return


class CAkDialogueEvent(CAkHircNode):
    def __init__(self):
        super(CAkDialogueEvent, self).__init__()
        self.ntid = None
        self.tree = None

    def _build(self, node):
        nbase = node.find1(name='DialogueEventInitialValues')

        # not sure how useful these are, don't exist in early versions either
        self.props = self._make_props(nbase)
        if self.props:
            self.props.barf_loop()

        self.tree = self._make_tree(node)
        return


class CAkAction(CAkHircNode):
    def __init__(self):
        super(CAkAction, self).__init__()
        self.ntid = None

    def _build(self, node):
        nbase = node.find1(name='ActionInitialValues')

        ntid = nbase.find(name='idExt')
        if not ntid: #older
            ntid = nbase.find(name='ulTargetID')
        self.ntid = ntid

        self.props = self._make_props(nbase)

        # common parent
        self._build_subaction(nbase)

    def _build_subaction(self, node):
        return


class CAkActionPlayAndContinue(CAkAction):
    def __init__(self):
        super(CAkActionPlayAndContinue, self).__init__()

    def _build_subaction(self, node):
        self._barf()


class CAkActionTrigger(CAkAction):
    def __init__(self):
        super(CAkActionTrigger, self).__init__()


class CAkActionPlay(CAkAction):
    def __init__(self):
        super(CAkActionPlay, self).__init__()
        self.nbankid = None

    def _build_subaction(self, node):
        nparams = node.find1(name='PlayActionParams')

        nbankid = nparams.find1(name='bankID')
        if not nbankid:
            nbankid = nparams.find1(name='fileID') #older
        # v26<= don't set bankID, automatically uses current
        self.nbankid = nbankid

class CAkActionPlayEvent(CAkActionPlay): #_CAkActionPlay
    def __init__(self):
        super(CAkActionPlayEvent, self).__init__()

    def _build_subaction(self, node):
        pass

#******************************************************************************
# ACTOR-MIXER HIERARCHY

class CAkParameterNode(CAkHircNode):
    def __init__(self):
        super(CAkHircNode, self).__init__()
    
    def _build(self, node):
        # audio nodes have common values (from subclassing) and their own, ex.
        #   CAkMusicTrack > SoundInitialValues > AkBankSourceData
        #                                      > NodeBaseParams
        #   CAkMusicTrack > MusicTrackInitialValues > pSource
        #                                           > NodeBaseParams

        self._build_nodebase(node)
        self._build_audionode(node)

    def _build_nodebase(self, node):

        nbase = node.find1(name='NodeBaseParams')
        if not nbase:
            self._barf('wrong parameter node')

        #NodeInitialFxParams: sfx list
        #byBitVector: misc unneeded config

        nbusid = nbase.find1(name='OverrideBusId')
        self.bbus = self._read_bus(nbusid)

        nparentid = nbase.find1(name='DirectParentID')
        self.bparent = self._read_parent(nparentid)

        #NodeInitialParams, sometimes
        self.props = self._make_props(nbase)

        #PositioningParams: object position stuff
        #AuxParams: aux-bus config
        #AdvSettingsParams: voice config etc

        #nstatechunk = nbase.find1(name='StateChunk')
        self.statechunk = self._make_statechunk(nbase)

        #InitialRTPC, note that exists outside NodeBaseParams
        ninitrtpc = nbase.find1(name='InitialRTPC')
        self.rtpclist = self._make_rtpclist(ninitrtpc)

        ninitfx = nbase.find1(name='NodeInitialFxParams')
        self.fxlist = self._make_fxlist(ninitfx)


    def _build_audionode(self, node):
        self._barf()


class CAkActorMixer(CAkParameterNode):
    def __init__(self):
        super(CAkActorMixer, self).__init__()

    def _build_audionode(self, node):
        # Actor-mixers are just a container of NodeBaseParams values, and sound nodes can set this as
        # parent to inherit them. There is a Children list but it's not used directly (no action calls this).
        pass


class CAkSwitchCntr(CAkParameterNode):
    def __init__(self):
        super(CAkSwitchCntr, self).__init__()
        self.gtype = None
        self.ngname = None
        self.gvalue_ntids = {}

    def _build_audionode(self, node):
        self.props.barf_loop() #unknown meaning

        self.gtype = node.find(name='eGroupType').value()
        self.ngname = node.find(name='ulGroupID')
        #ulDefaultSwitch: not used since we create all combos (must point to a valid path, or 0=none)
        #bIsContinuousValidation: step/continuous mode?
        #ulNumSwitchParams: info for switches (ex. FadeOutTime/FadeInTime)
        #children: same as NodeList

        ngvalues = node.find(name='SwitchList').finds(name='ulSwitchID')
        for ngvalue in ngvalues:
            ntids = ngvalue.get_parent().find(name='NodeList').finds(type='tid')
            if not ntids: #may define an empty path
                continue
            gvalue = ngvalue.value()
            self.gvalue_ntids[gvalue] = (ntids, ngvalue)
        return


class CAkRanSeqCntr(CAkParameterNode):
    def __init__(self):
        super(CAkRanSeqCntr, self).__init__()
        self.ntids = []

    def _build_audionode(self, node):
        self.props.barf_loop() #should have its own loop property below

        #bIsGlobal: this object is a global entity (not needed, affects sequences/shuffles/etc)
        nmode = node.find(name='eMode')  #0=random / 1=sequence
        nrandom = node.find(name='eRandomMode')  #0=normal (repeatable), 1=shuffle (no repeatable)
        ncontinuous = node.find(name='bIsContinuous')  #play one of the objects each time this is played, else play all
        navoidrepeat = node.find(name='wAvoidRepeatCount')  #excludes last played object from available list until N are played

        self.mode = nmode.value()
        self.random = nrandom.value()
        self.continuous = ncontinuous.value()
        self.avoidrepeat = navoidrepeat.value()

        nloop = node.find(name='sLoopCount')  #1=once, 0=infinite, >1=N times
        nloopmin = node.find(name='sLoopModMin') #v72> random loop modifiers (loop -min +max)
        nloopmax = node.find(name='sLoopModMax') #v72>

        # loop ignored by Wwise but sometimes set, simplify
        if nloop.value() == 0 and not self.continuous:
            pass
        else:
            self.props.set_loop(nloop, nloopmin, nloopmax)

            self.fields.prop(nloop)


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

        self.fields.props([nmode, nrandom, nloop, ncontinuous, navoidrepeat])
        return


class CAkLayerCntr(CAkParameterNode):
    def __init__(self):
        super(CAkLayerCntr, self).__init__()
        self.ntids = []
        self.layer_rtpclist = None

    def _build_audionode(self, node):
        self.props.barf_loop() #unknown meaning

        nmode = node.find(name='bIsContinuousValidation')

        #if nmode: #newer only
        #if   mode == 0: #step (plays all at the same time, may loop or stop once all done)
        #elif mode == 1: #continuous (keeps playing nodes in RTPC region)

        self.ntids = node.find(name='Children').finds(type='tid')

        # usually found with RTPCs (ex. RPMs) + pLayers that define when layers are played
        nlayers = node.find1(name='pLayers')
        if nlayers:
            #TODO: layers have a base RTPC (read above) and a graph of children nodes <> RTPC value, but not sure how it works

            # RTPC linked to volume (ex. AC2 bgm+crowds)
            self.layer_rtpclist = self._make_rtpclist(nlayers)

        if nmode:
            self.fields.prop(nmode)
        return


class CAkSound(CAkParameterNode):
    def __init__(self):
        super(CAkSound, self).__init__()
        self.sound = hnode_misc.NodeSound()

    def _build_audionode(self, node):

        nloop = node.find(name='Loop')
        if nloop: #older
            nloopmin = node.find(name='LoopMod.min')
            nloopmax = node.find(name='LoopMod.max')
            self.props.set_loop(nloop, nloopmin, nloopmax)

            self.fields.prop(nloop)


        nitem = node.find(name='AkBankSourceData')
        source = self._make_source(nitem)
        self.sound.source = source
        self.sound.nsrc = source.nfileid

        self.fields.prop(source.nstreamtype)
        if source.nsourceid != source.nfileid:
            self.fields.prop(source.nfileid)
        return

#******************************************************************************
# INTERACTIVE MUSIC HIERARCHY

class CAkMusicSwitchCntr(CAkParameterNode):
    def __init__(self):
        super(CAkMusicSwitchCntr, self).__init__()
        self.gtype = None
        self.ngname = None
        self.gvalue_ntid = {}
        self.ntid = False
        self.rules = None
        self.tree = None

    def _build_audionode(self, node):
        self.rules = self._make_transition_rules(node, True)
        self.stingerlist = self._make_stingerlist(node)

        #Children: list, also in nodes
        #bIsContinuePlayback: ?
        #uMode: 0=BestMatch/1=Weighted

        self.tree = self._make_tree(node)
        if not self.tree:
            # earlier versions work like a normal switch and don't have a tree
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


class CAkMusicRanSeqCntr(CAkParameterNode):
    def __init__(self):
        super(CAkMusicRanSeqCntr, self).__init__()
        self.items = []
        self.rules = None

    def _build_audionode(self, node):
        self.props.barf_loop() #unknown meaning

        self.rules = self._make_transition_rules(node, False)
        self.stingerlist = self._make_stingerlist(node)

        self.fields.rules(self.rules)

        #playlists are "groups" that include 'leaf' objects or other groups
        # ex. item: playlist (sequence)
        #       item: segment A
        #       item: segment B
        #       item: playlist (random)
        #         item: segment C
        #         item: segment D
        # may play on loop: ABC ABC ABD ABC ABD ... (each group has its own loop info)
        nplaylist = node.find1(name='pPlayList')
        self._build_playlist(node, nplaylist, self.items)

    def _build_playlist(self, node, nplaylist, items):
        #get AkMusicRanSeqPlaylistItem, but only for current level (as playlists can contain playlists)
        nitems = nplaylist.get_children() #only direct
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

            item = AkMusicRanSeqPlaylistItem()
            item.nitem = nitem
            item.ntid = ntid
            item.type = type
            item.loop = nloop.value()
            item.fields.props([ntype, nloop])

            items.append(item)

            self._build_playlist(node, nsubplaylist, item.items)
        return

class AkMusicRanSeqPlaylistItem(object):
    def __init__(self):
        self.nitem = None
        self.ntid = None
        self.type = None
        self.loop = None
        self.fields = wtxtp_fields.TxtpFields()
        self.items = []


class CAkMusicSegment(CAkParameterNode):
    def __init__(self):
        super(CAkMusicSegment, self).__init__()
        self.ntids = []
        self.sound = None
        self.duration = None
        self.entry = None
        self.exit = None

    def _build_audionode(self, node):
        self.props.barf_loop() #unknown meaning

        self.stingerlist = self._make_stingerlist(node)

        # main duration
        nfdur = node.find(name='fDuration')
        # AkMeterInfo: for switches

        self.duration = nfdur.value()
        self.fields.prop(nfdur)

        # markers for transitions
        markers = AkMarkerList(node)
        marker1 = markers.get_entry()
        marker2 = markers.get_exit()

        self.entry = marker1.pos
        self.exit = marker2.pos
        self.fields.keyval(marker1.node, marker1.npos)
        self.fields.keyval(marker2.node, marker2.npos)

        # music track list
        self.ntids = node.find(name='Children').finds(type='tid')
        if not self.ntids:
            # empty segments are allowed as silence
            sound = hnode_misc.NodeSound()
            sound.nsrc = self.node
            sound.silent = True
            sound.clip = True
            self.sound = sound
        return


class CAkMusicTrack(CAkParameterNode):
    def __init__(self):
        super(CAkMusicTrack, self).__init__()
        self.type = None
        self.subtracks = []
        self.gtype = None
        self.ngname = None
        self.gvalue_indexes = {}
        self.gvalue_names = {}
        self.automationlist = {}
        self.silence = None
        self.unreachables = []

    def _build_audionode(self, node):
        self._build_silence()

        nloop = node.find(name='Loop')
        if nloop: #older
            nloopmin = node.find(name='LoopMod.min')
            nloopmax = node.find(name='LoopMod.max')
            self.props.set_loop(nloop, nloopmin, nloopmax)

            self.fields.prop(nloop)


        # loops in MusicTracks are meaningless, ignore to avoid confusing the parser
        self.props.disable_loop()

        # prepare for clips
        self.automationlist = self._make_automationlist(node)

        ntype = node.find(name='eTrackType')
        if not ntype:
            ntype = node.find(name='eRSType')
        self.type = ntype.value()

        # save info about sources for later
        streaminfos = {}
        nitems = node.find1(name='pSource').finds(name='AkBankSourceData')
        for nitem in nitems:
            source = self._make_source(nitem)
            tid = source.nsourceid.value()
            streaminfos[tid] = source

        # match musictracks sources to subtracks. First it defines AkBankSourceData,
        # then it sets "subtracks" which may use those sources. They don't map 1:1,
        # rather 1 track may use N sources as part of clips. Usually there is only 1 track
        # but multiple are possible other eTrackTypes. It's also possible to define N sources
        # yet only use 1 (leftover unused data).

        # each track contains N "clips" (srcs):
        # - 0: silent track (ex. Astral Chain 517843579)
        # - 1: normal
        # - N: layered clips with fades if overlapped (pre-defined)
        # Final length size depends on segment
        ncount = node.find1(name='numSubTrack')
        if not ncount: #empty / no clips
            return

        self.subtracks = [None] * ncount.value()

        # map clips to subtracks
        index = 0
        nsrcs = node.finds(name='AkTrackSrcInfo')
        for nsrc in nsrcs:
            track = nsrc.find(name='trackID').value()
            if not self.subtracks[track]:
                self.subtracks[track] = []

            clip = self._build_clip(streaminfos, nsrc)
            clip.sound.automations = self.automationlist.get(index)

            self.subtracks[track].append(clip)
            index += 1

        # pre-parse switch variables
        if self.type == 3:
            #TransParams: define switch transition
            nswitches = node.find(name='SwitchParams')
            self.gtype = nswitches.find(name='eGroupType').value()
            self.ngname = nswitches.find(name='uGroupID')
            ngvdefault = nswitches.find(name='uDefaultSwitch')

            ngvalues = nswitches.finds(name='ulSwitchAssoc')
            for ngvalue in ngvalues: #switch N = track N
                gvalue = ngvalue.value()
                index = ngvalue.get_parent().get_index()

                # rare but same ID may set N tracks (FE:E)
                if gvalue not in self.gvalue_indexes:
                    self.gvalue_indexes[gvalue] = []
                    self.gvalue_names[gvalue] = ngvalue
                self.gvalue_indexes[gvalue].append(index)

            # NMH3 uses default to play no subtrack (base) + one ulSwitchAssoc to play subtrack (base+extra)
            # maybe should also add "value none"
            gvdefault = ngvdefault.value()
            if gvdefault not in self.gvalue_indexes:
                self.gvalue_indexes[gvdefault] = [] #none to force "don't play any subtrack"
                self.gvalue_names[gvdefault] = ngvdefault

            # maybe should include "any other state"?
            #self.gvalue_index[None] = [None] #None to force "don't play any subtrack"

        # detect unused sources by finding sources in clips
        # (Tribe Nine's bank_Play_Music_XB.bnk: 469329726, Lego Horizon MUS_MusicAll.bnk: 865368961, some ACs Sea Shanties, etc)
        streaminfos_used = []
        for clips in self.subtracks:
            if not clips:
                continue
            for clip in clips:
                # possible when clips use event IDs
                if not clip.sound or not clip.sound.nsrc: 
                    continue
                tid = clip.sound.nsrc.value()
                streaminfos_used.append(tid)
        for tid in streaminfos:
            if tid in streaminfos_used:
                continue
            source = streaminfos[tid]
            sound = self._build_unreachable(source)
            self.unreachables.append(sound)

        self.fields.props([ntype, ncount])
        self.fields.automations(self.automationlist)
        return

    def _build_silence(self):
        # for (rare) cases that no track is defined
        sound = hnode_misc.NodeSound()
        sound.nsrc = self.node
        sound.silent = True
        sound.clip = True
        self.silence = sound

    def _build_clip(self, streaminfos, nsrc):
        nfpa = nsrc.find(name='fPlayAt')
        nfbt = nsrc.find(name='fBeginTrimOffset')
        nfet = nsrc.find(name='fEndTrimOffset')
        nfsd = nsrc.find(name='fSrcDuration')
        nsourceid = nsrc.find(name='sourceID')
        neventid = nsrc.find(name='eventID') #later versions

        clip = CAkMusicTrack_Clip()
        clip.nitem = nsrc
        clip.neid = neventid
        clip.fields.props([nsourceid, neventid, nfpa, nfbt, nfet, nfsd])

        clip.sound.fpa = nfpa.value()
        clip.sound.fbt = nfbt.value()
        clip.sound.fet = nfet.value()
        clip.sound.fsd = nfsd.value()

        # sometimes sourceid 0 is used, meaning it has an eventid. But rarely
        # AkBankSourceData with source id 0 and plugin "none" exits (South Park: Stick of Truth, ZoE2 HD)
        sourceid = nsourceid.value()
        source = streaminfos.get(sourceid)
        if source:
            clip.sound.source = source
            clip.sound.nsrc = source.nsourceid

            clip.fields.prop(source.nstreamtype)
            if source.nsourceid != source.nfileid:
                clip.fields.prop(source.nfileid)

        # possible in ZoE2 HD us0001f436.bnk's 937118865 (allowed as silence)
        #elif not neventid:
        #    self._barf("no source nor eventid found, report")

        return clip

    def _build_unreachable(self, source):
        # for (rare) cases that no track is defined
        sound = hnode_misc.NodeSound()
        sound.source = source
        sound.nsrc = source.nsourceid
        sound.unreachable = True
        sound.clip = True #treat as clip as it's needed as part of segments
        return sound

class CAkMusicTrack_Clip(object):
    def __init__(self):
        self.nitem = None
        self.ntid = None
        self.neid = None
        self.sound = hnode_misc.NodeSound()
        self.sound.clip = True
        self.fields = wtxtp_fields.TxtpFields()
