from . import bnode_automation, bnode_misc
from ..txtp import wtxtp_info

from .bnode_base import CAkHircNode
from .bnode_markers import AkMarkerList


#non-audio node, doesn't contribute to txtp
class CAkNone(CAkHircNode):
    def __init__(self):
        super(CAkNone, self).__init__()

    def _build(self, node):
        #ignore
        return

#non-audio node, but it's used as a reference
class CAkState(CAkHircNode):
    def __init__(self):
        super(CAkState, self).__init__()

    def _build(self, node):
        self._build_audio_config(node)
        #save config (used to check silences)
        return

#plugin parameters, sometimes needed
class CAkFxCustom(CAkHircNode):
    def __init__(self):
        super(CAkFxCustom, self).__init__()
        self.fx = None

    def _build(self, node):
        #save config (used for sources)
        nfxid = node.find1(name='fxID')
        plugin_id = nfxid.value()

        self.fx = self._build_sfx(node, plugin_id)
        return

#******************************************************************************
# EVENTS AND ACTIONS

class CAkEvent(CAkHircNode):
    def __init__(self):
        super(CAkEvent, self).__init__()
        self.ntids = None

    def _build(self, node):
        #EventInitialValues
        self.ntids = node.finds(name='ulActionID')
        # events that don't call anything seem trimmed so this should exist
        return


class CAkDialogueEvent(CAkHircNode):
    def __init__(self):
        super(CAkDialogueEvent, self).__init__()
        self.ntid = None
        self.tree = None

    def _build(self, node):
        self._build_audio_config(node)
        if self.config.loop is not None:
            self._barf("loop flag")

        tree = self._build_tree(node)
        if tree.init:
            self.tree = tree


class CAkAction(CAkHircNode):
    def __init__(self):
        super(CAkAction, self).__init__()
        self.ntid = None

    def _build(self, node):
        self._build_action(node)

        ntid = node.find(name='idExt')
        if not ntid: #older
            ntid = node.find(name='ulTargetID')
        self.ntid = ntid

        self._build_subaction(node)

    def _build_subaction(self, node):
        return


class CAkActionPlayAndContinue(CAkAction):
    def __init__(self):
        super(CAkActionPlayAndContinue, self).__init__()

    def _build(self, node):
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
        if nparams:
            nbankid = node.find1(name='bankID')
            if not nbankid:
                nbankid = node.find1(name='fileID') #older
            # v26<= don't set bankID, automatically uses current
            self.nbankid = nbankid


class CAkActionPlayEvent(CAkActionPlay): #_CAkActionPlay
    def __init__(self):
        super(CAkActionPlayEvent, self).__init__()


#******************************************************************************
# ACTOR-MIXER HIERARCHY


class CAkActorMixer(CAkHircNode):
    def __init__(self):
        super(CAkHircNode, self).__init__()

    def _build(self, node):
        # Actor-mixers are just a container of common values, and sound nodes can set this as parent to inherit them.
        # There is a child list but it's not used directly (no action calls this).
        pass


class CAkSwitchCntr(CAkHircNode):
    def __init__(self):
        super(CAkSwitchCntr, self).__init__()
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


class CAkRanSeqCntr(CAkHircNode):
    def __init__(self):
        super(CAkRanSeqCntr, self).__init__()
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


class CAkLayerCntr(CAkHircNode):
    def __init__(self):
        super(CAkLayerCntr, self).__init__()
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
            self._build_rtpc(nlayers)

        if nmode:
            self.fields.prop(nmode)
        return


class CAkSound(CAkHircNode):
    def __init__(self):
        super(CAkSound, self).__init__()
        self.sound = bnode_misc.NodeSound()

    def _build(self, node):
        self._build_audio_config(node)

        nloop = node.find(name='Loop')
        if nloop: #older
            self.config.loop = nloop.value()
            self.fields.prop(nloop)
            #there is min/max too

        nitem = node.find(name='AkBankSourceData')
        source = self._build_source(nitem)
        self.sound.source = source
        self.sound.nsrc = source.nfileid

        self.fields.prop(source.nstreamtype)
        if source.nsourceid != source.nfileid:
            self.fields.prop(source.nfileid)
        return

#******************************************************************************
# INTERACTIVE MUSIC HIERARCHY

class CAkMusicSwitchCntr(CAkHircNode):
    def __init__(self):
        super(CAkMusicSwitchCntr, self).__init__()
        self.gtype = None
        self.ngname = None
        self.gvalue_ntid = {}
        self.has_tree = None
        self.ntid = False
        self.rules = None
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


class CAkMusicRanSeqCntr(CAkHircNode):
    def __init__(self):
        super(CAkMusicRanSeqCntr, self).__init__()
        self.items = []
        self.rules = None

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

            item = CAkMusicRanSeqCntr_Item()
            item.nitem = nitem
            item.ntid = ntid
            item.type = type
            item.config.loop = nloop.value()
            item.fields.props([ntype, nloop])
             
            items.append(item)

            self._playlist(node, nsubplaylist, item.items)
        return

class CAkMusicRanSeqCntr_Item():
    def __init__(self):
        self.nitem = None
        self.ntid = None
        self.type = None
        self.config = bnode_misc.NodeConfig()
        self.fields = wtxtp_info.TxtpFields()
        self.items = []


class CAkMusicSegment(CAkHircNode):
    def __init__(self):
        super(CAkMusicSegment, self).__init__()
        self.ntids = []
        self.sound = None
        self.sconfig = None

    def _build(self, node):
        self._build_audio_config(node)
        if self.config.loop is not None:
            self._barf("loop flag")
        self._build_stingers(node)

        # main duration
        nfdur = node.find(name='fDuration')
        # AkMeterInfo: for switches

        self.config.duration = nfdur.value()
        self.fields.prop(nfdur)

        # markers for transitions
        markers = AkMarkerList(node)
        marker1 = markers.get_entry()
        marker2 = markers.get_exit()

        self.config.entry = marker1.pos
        self.config.exit = marker2.pos
        self.fields.keyval(marker1.node, marker1.npos)
        self.fields.keyval(marker2.node, marker2.npos)

        # music track list
        self.ntids = node.find(name='Children').finds(type='tid')
        if not self.ntids:
            # empty segments are allowed as silence
            self.sound = self._build_silence(self.node, True)
            self.sconfig = bnode_misc.NodeConfig()
        return


class CAkMusicTrack(CAkHircNode):
    def __init__(self):
        super(CAkMusicTrack, self).__init__()
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
        self.automations = bnode_automation.AkClipAutomationList(node)

        ntype = node.find(name='eTrackType')
        if not ntype:
            ntype = node.find(name='eRSType')
        self.type = ntype.value()

        # save info about sources for later
        streaminfos = {}
        nitems = node.find1(name='pSource').finds(name='AkBankSourceData')
        for nitem in nitems:
            source = self._build_source(nitem)
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

        # pre-parse switch variables
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

        clip = CAkMusicTrack_Clip()
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

class CAkMusicTrack_Clip(CAkHircNode):
    def __init__(self):
        self.nitem = None
        self.ntid = None
        self.neid = None
        self.sound = bnode_misc.NodeSound()
        self.sound.clip = True
        self.fields = wtxtp_info.TxtpFields()
