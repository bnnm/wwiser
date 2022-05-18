from .bnode_hircs import *


# default for non-useful HIRC classes
_DEFAULT_BUILDER_NODE = CAkNone

# HIRC classes and their rebuilt equivalent.
# Internal classes (like AkTrackSrcInfo) are handled separately per class since they
# tend to need custom behavior
_HIRC_BUILDER_NODES = {
    # actions
    'CAkEvent': CAkEvent,
    'CAkDialogueEvent': CAkDialogueEvent,
    'CAkActionPlay': CAkActionPlay,
    'CAkActionTrigger': CAkActionTrigger,

    # not found, may need to do something with them
    'CAkActionPlayAndContinue': CAkActionPlayAndContinue,
    'CAkActionPlayEvent': CAkActionPlayEvent,

    # sound hierarchy
    'CAkActorMixer': CAkActorMixer,
    'CAkLayerCntr': CAkLayerCntr,
    'CAkSwitchCntr': CAkSwitchCntr,
    'CAkRanSeqCntr': CAkRanSeqCntr,
    'CAkSound': CAkSound,

    # music hierarchy
    'CAkMusicSwitchCntr': CAkMusicSwitchCntr,
    'CAkMusicRanSeqCntr': CAkMusicRanSeqCntr,
    'CAkMusicSegment': CAkMusicSegment,
    'CAkMusicTrack': CAkMusicTrack,

    # others
    'CAkState': CAkState,
    'CAkFxCustom': CAkFxCustom,
    'CAkBus': CAkBus,

    #not useful
    #CAkActionSetState
    #CAkAction*
    #CAkAuxBus
    #CAkFeedbackBus: accepts audio from regular sounds + creates rumble
    #CAkFeedbackNode: played like audio (play action) and has source ID, but it's simply a rumble generator
    #CAkAttenuation
    #CAkAudioDevice
    #CAkFxShareSet
    #CAkLFOModulator
    #CAkEnvelopeModulator
    #CAkTimeModulator
}

def get_builder_hirc_class(hircname):
    return _HIRC_BUILDER_NODES.get(hircname, _DEFAULT_BUILDER_NODE)


# Classes that may generate unused audio, ordered by priority (musicsegment may contain unused musictrack)
UNUSED_HIRCS = [
    #'CAkEvent',
    #'CAkDialogueEvent',
    'CAkActionPlay',
    'CAkActionTrigger',

    'CAkActionPlayAndContinue',
    'CAkActionPlayEvent',

    'CAkLayerCntr',
    'CAkSwitchCntr',
    'CAkRanSeqCntr',
    'CAkSound',

    'CAkMusicSwitchCntr',
    'CAkMusicRanSeqCntr',
    'CAkMusicSegment',
    'CAkMusicTrack',
]


# Wwise separates shortIDs into:
# - explicit: internal use only (guidnames for most objects)
# - implicit: external use (hashnames for events, switches, states, rtpcs, textures)
# - media: .wem, same as explicit.
#
# ShortIDs can be reused between types, so it's possible to have an event, dialogueevent, bus and
# aksound with the same ID (not that common though), while you can't have 2 buses named the same
# (even aux-bus + bus).
# 
# Explicit objects won't repeat IDs *in the same bank* (no aksound + akswitch with same ID) but
# hashnames can match explicit IDs. Devs could also make one aksound in one bank, compile, change the
# aksound's source and make another bank, in effect 2 different audio objects with the same ID,
# so bank is also taken into account (seen in Detroit).
#
# This means when loading/reading another object we need to know the type, to allow certain repeated
# IDs (though it's rare). Not all named objects in the editor have an hashname though.
#
# implicits
IDTYPE_EVENT = 0
IDTYPE_DIALOGUEEVENT = 1
# not used directly in hircs (kind of implicit)
IDTYPE_STATE_GROUP = 2
IDTYPE_STATE_VALUE = 3
IDTYPE_SWITCH_GROUP = 4
IDTYPE_SWITCH_VALUE = 5
IDTYPE_GAMEPARAMETER = 6
IDTYPE_TRIGGER = 7
IDTYPE_ARGUMENTS = 8 #old dialogueevent args, uses switches or states in later versions

# actor-mixer / interactive music (guidnames)
IDTYPE_AUDIO = 10
# master-mixer (usually a hashname)
IDTYPE_BUS = 20
# share sets > effects
IDTYPE_EFFECT = 30
# from tests
IDTYPE_AUDIODEVICE = 40


_IDTYPE_HIRCS = {
    # event/implicit
    'CAkEvent': IDTYPE_EVENT,
    'CAkDialogueEvent': IDTYPE_DIALOGUEEVENT,

    # buses
    'CAkBus': IDTYPE_BUS,
    'CAkAuxBus': IDTYPE_BUS,
    'CAkFeedbackBus': IDTYPE_BUS, #untested

    'CAkFxShareSet': IDTYPE_EFFECT,

    'CAkAudioDevice': IDTYPE_AUDIODEVICE,

    # audio (default since most objects are this)
    #CAkAction*

    #CAkActorMixer
    #CAkLayerCntr
    #CAkSwitchCntr
    #CAkRanSeqCntr
    #CAkSound

    #CAkMusicSwitchCntr
    #CAkMusicRanSeqCntr
    #CAkMusicSegment
    #CAkMusicTrack

    #CAkState  #audio objects, despite the name
    #CAkFeedbackNode  #assumed, played like audio

    #CAkLFOModulator  #can be named in editor, but internally uses guidnames
    #CAkEnvelopeModulator  #same
    #CAkTimeModulator  #same
    #CAkAttenuation  #assumed to be the same
    #CAkFxCustom:  #assumed, not using hashnames
}


def get_builder_hirc_idtype(hircname):
    return _IDTYPE_HIRCS.get(hircname, IDTYPE_AUDIO)
