from .wrenderer_nodes import *


# HIRC classes that should be used to generate .txtp
GENERATED_BASE_HIRCS =  [
    'CAkEvent',
    'CAkDialogueEvent',
]

# default for non-useful HIRC classes
_DEFAULT_RENDERER_NODE = RN_CAkNone

# HIRC classes capable of making a TXTP part.
# Each should also have a bnode equivalent 
_HIRC_RENDERER_NODES = {
    # action classes
    'CAkEvent': RN_CAkEvent,
    'CAkDialogueEvent': RN_CAkDialogueEvent,
    'CAkActionPlay': RN_CAkActionPlay,
    'CAkActionTrigger': RN_CAkActionTrigger,
    # not found, may need to do something with them
    'CAkActionPlayAndContinue': RN_CAkActionPlayAndContinue,
    'CAkActionPlayEvent': RN_CAkActionPlayEvent,

    # sound engine
    'CAkLayerCntr': RN_CAkLayerCntr,
    'CAkSwitchCntr': RN_CAkSwitchCntr,
    'CAkRanSeqCntr': RN_CAkRanSeqCntr,
    'CAkSound': RN_CAkSound,

    # music engine
    'CAkMusicSwitchCntr': RN_CAkMusicSwitchCntr,
    'CAkMusicRanSeqCntr': RN_CAkMusicRanSeqCntr,
    'CAkMusicSegment': RN_CAkMusicSegment,
    'CAkMusicTrack': RN_CAkMusicTrack,

    # info only, not renderable
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
