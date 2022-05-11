from .wrebuilder_nodes import *


# default for non-useful HIRC classes
_DEFAULT_BUILDER_NODE = CAkNone

# HIRC classes and their rebuilt equivalent.
# Internal classes (like AkTrackSrcInfo) are handled separately per class since they
# tend to need custom behavior
_HIRC_BUILDER_NODES = {
    # base
    'CAkEvent': CAkEvent,
    'CAkDialogueEvent': CAkDialogueEvent,
    'CAkActionPlay': CAkActionPlay,
    'CAkActionTrigger': CAkActionTrigger,

    # not found, may need to do something with them
    'CAkActionPlayAndContinue': CAkActionPlayAndContinue,
    'CAkActionPlayEvent': CAkActionPlayEvent,

    # sound engine
    'CAkLayerCntr': CAkLayerCntr,
    'CAkSwitchCntr': CAkSwitchCntr,
    'CAkRanSeqCntr': CAkRanSeqCntr,
    'CAkSound': CAkSound,

    # music engine
    'CAkMusicSwitchCntr': CAkMusicSwitchCntr,
    'CAkMusicRanSeqCntr': CAkMusicRanSeqCntr,
    'CAkMusicSegment': CAkMusicSegment,
    'CAkMusicTrack': CAkMusicTrack,

    # others
    'CAkStinger': CAkStinger,
    'CAkState': CAkState,
    'CAkFxCustom': CAkFxCustom, #similar to CAkFeedbackNode but config only (referenced in AkBankSourceData)

    #not useful
    #CAkActorMixer
    #CAkActionSetState
    #CAkAction*
    #CAkBus
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

def get_builder_hirc(hircname):
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
