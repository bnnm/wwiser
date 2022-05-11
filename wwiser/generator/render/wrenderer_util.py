from . import wrenderer_nodes as rn


GENERATED_BASE_HIRCS =  [
    'CAkEvent',
    'CAkDialogueEvent',
]

# default for non-useful HIRC classes
_DEFAULT_RENDERER_NODE = rn._CAkNone

# HIRC classes and their rebuilt equivalent.
# Internal classes (like AkTrackSrcInfo) are handled separately per class since they
# tend to need custom behavior
_HIRC_RENDERER_NODES = {
    # base
    'CAkEvent': rn._CAkEvent,
    'CAkDialogueEvent': rn._CAkDialogueEvent,
    'CAkActionPlay': rn._CAkActionPlay,
    'CAkActionTrigger': rn._CAkActionTrigger,

    # not found, may need to do something with them
    'CAkActionPlayAndContinue': rn._CAkActionPlayAndContinue,
    'CAkActionPlayEvent': rn._CAkActionPlayEvent,

    # sound engine
    'CAkLayerCntr': rn._CAkLayerCntr,
    'CAkSwitchCntr': rn._CAkSwitchCntr,
    'CAkRanSeqCntr': rn._CAkRanSeqCntr,
    'CAkSound': rn._CAkSound,

    # music engine
    'CAkMusicSwitchCntr': rn._CAkMusicSwitchCntr,
    'CAkMusicRanSeqCntr': rn._CAkMusicRanSeqCntr,
    'CAkMusicSegment': rn._CAkMusicSegment,
    'CAkMusicTrack': rn._CAkMusicTrack,

    #not an action
    #CAkStinger
    #CAkState
    #CAkFxCustom
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

def get_renderer_hirc(hircname):
    return _HIRC_RENDERER_NODES.get(hircname, _DEFAULT_RENDERER_NODE)


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

