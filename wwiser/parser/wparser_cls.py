from . import wmodel
#from . import wparser
wparser = None #needed for circular refs in python <3.7, see setup()


#******************************************************************************
# VTABLE HELPERS

# Some functions use callbacks/vtables due to inheritance, so we need to simulate
# it with a container with callbacks to pass around
#
# Doesn't emulate the full-blown subclassing model, since decompiled code doesn't
# either (virtual functions calls are more expensive) and it'd make harder to
# follow/compare SDKs.
#
# Common class inheritance paths:

# CAkAction
#  CAkActionExcept : CAkAction
#   CAkActionActive : CAkActionExcept
#    CAkActionSetValue : CAkActionExcept

# CAkRTPCSubscriberNode
# CAkStateAware
#  CAkFxBaseStateAware : CAkStateAware
# CAkIndexable
#  CAkParamNodeStateAware : CAkStateAware
#  CAkPBIAware : CAkIndexable #CAkIndexableObj in v168
#   CAkParameterNodeBase : CAkPBIAware, CAkParamNodeStateAware, CAkRTPCSubscriberNode
#    CAkParameterNode : CAkParameterNodeBase
#     CAkSoundBase : CAkParameterNode
#     CAkParentNode<CAkParameterNode> : CAkParameterNode
#      CAkActiveParent<CAkParameterNode> : CAkParentNode<CAkParameterNode>
#       CAkMusicNode : CAkActiveParent<CAkParameterNode>
#        CAkMusicTransAware : CAkMusicNode
#       CAkContainerBase : CAkActiveParent<CAkParameterNode>
#        CAkMultiPlayNode : CAkContainerBase
#     CAkActiveParent<CAkParameterNodeBase> : CAkParentNode<CAkParameterNode>
#  CAkFxBase : CAkIndexable, CAkFxBaseStateAware
#  CAkModulator : CAkIndexable
# CAkPreparationAware
# CAkSwitchAware

#CAkSound : CAkSoundBase
CAkSound = 'CAkSound'
#CAkState : CAkIndexable
CAkState = 'CAkState'
#CAkActionStop : CAkActionActive
CAkActionStop = 'CAkActionStop'
#CAkActionPause : CAkActionActive
CAkActionPause = 'CAkActionPause'
#CAkActionResume : CAkActionActive
CAkActionResume = 'CAkActionResume'
#CAkActionPlay : CAkAction
CAkActionPlay = 'CAkActionPlay'
#CAkActionPlayAndContinue : CAkActionPlay
CAkActionPlayAndContinue = 'CAkActionPlayAndContinue'
#CAkActionMute : CAkActionSetValue
CAkActionMute = 'CAkActionMute'
#CAkActionSetPitch : CAkActionSetValue
CAkActionSetPitch = 'CAkActionSetPitch'
#CAkActionSetVolume : CAkActionSetValue
CAkActionSetVolume = 'CAkActionSetVolume'
#CAkActionSetLFE : CAkActionSetValue
CAkActionSetLFE = 'CAkActionSetLFE'
#CAkActionSetLPF : CAkActionSetValue
CAkActionSetLPF = 'CAkActionSetLPF'
#CAkActionSetAkProp (AkPropID_xxx) : CAkActionSetValue
CAkActionSetAkProp = 'CAkActionSetAkProp'
#CAkActionUseState : CAkAction
CAkActionUseState = 'CAkActionUseState'
#CAkActionSetState : CAkAction
CAkActionSetState = 'CAkActionSetState'
#CAkActionSetGameParameter : CAkActionSetValue
CAkActionSetGameParameter = 'CAkActionSetGameParameter'
#CAkActionEvent : CAkAction
CAkActionEvent = 'CAkActionEvent'
#CAkActionDuck : CAkAction
CAkActionDuck = 'CAkActionDuck'
#CAkActionSetSwitch : CAkAction
CAkActionSetSwitch = 'CAkActionSetSwitch'
#CAkActionSetRTPC : CAkAction
CAkActionSetRTPC = 'CAkActionSetRTPC'
#CAkActionBypassFX : CAkActionExcept
CAkActionSetFX = 'CAkActionSetFX'
#CAkActionBypassFX : CAkActionExcept
CAkActionBypassFX = 'CAkActionBypassFX'
#CAkActionBreak : CAkAction
CAkActionBreak = 'CAkActionBreak'
#CAkActionTrigger : CAkAction
CAkActionTrigger = 'CAkActionTrigger'
#CAkActionSeek : CAkActionExcept
CAkActionSeek = 'CAkActionSeek'
#CAkActionRelease : CAkActionActive
CAkActionRelease = 'CAkActionRelease'
#CAkActionPlayEvent : CAkAction
CAkActionPlayEvent = 'CAkActionPlayEvent'
#CAkActionResetPlaylist : CAkActionActive
CAkActionResetPlaylist = 'CAkActionResetPlaylist'
#CAkActionResetPlaylist : CAkActionActive
CAkActionPlayEventUnknown = 'CAkActionPlayEventUnknown'
#CAkEvent : CAkIndexable
CAkEvent = 'CAkEvent'
#CAkRanSeqCntr : CAkContainerBase
CAkRanSeqCntr = 'CAkRanSeqCntr'
#CAkSwitchCntr : CAkMultiPlayNode, CAkSwitchAware, CAkPreparationAware
CAkSwitchCntr = 'CAkSwitchCntr'
#CAkActorMixer : CAkActiveParent<CAkParameterNode>
CAkActorMixer = 'CAkActorMixer'
#CAkBus : CAkActiveParent<CAkParameterNodeBase>
CAkBus = 'CAkBus'
#CAkLayerCntr : CAkMultiPlayNode
CAkLayerCntr = 'CAkLayerCntr'
#CAkMusicSegment : CAkMusicNode
CAkMusicSegment = 'CAkMusicSegment'
#CAkMusicTrack : CAkSoundBase
CAkMusicTrack = 'CAkMusicTrack'
#CAkMusicSwitchCntr : CAkMusicTransAware, CAkPreparationAware
CAkMusicSwitchCntr = 'CAkMusicSwitchCntr'
#CAkMusicRanSeqCntr : CAkMusicTransAware
CAkMusicRanSeqCntr = 'CAkMusicRanSeqCntr'
#CAkAttenuation : CAkIndexable
CAkAttenuation = 'CAkAttenuation'
#CAkDialogueEvent : CAkIndexable
CAkDialogueEvent = 'CAkDialogueEvent'
#CAkFeedbackBus : CAkBus
CAkFeedbackBus = 'CAkFeedbackBus'
#CAkFeedbackNode : CAkParameterNode
CAkFeedbackNode = 'CAkFeedbackNode'
#CAkFxShareSet : CAkFxBase
CAkFxShareSet = 'CAkFxShareSet'
#CAkFxCustom : CAkFxBase
CAkFxCustom = 'CAkFxCustom'
#CAkAuxBus : CAkBus
CAkAuxBus = 'CAkAuxBus'
#CAkLFOModulator : CAkModulator
CAkLFOModulator = 'CAkLFOModulator'
#CAkEnvelopeModulator : CAkModulator
CAkEnvelopeModulator = 'CAkEnvelopeModulator'
#CAkAudioDevice : CAkFxBase
CAkAudioDevice = 'CAkAudioDevice'
#CAkTimeModulator : CAkModulator
CAkTimeModulator = 'CAkTimeModulator'
#CAkSidechainMixIndexable : CAkIndexBase
CAkSidechainMixIndexable = 'CAkSidechainMixIndexable'



class AkClass:
    def __init__(self, obj, name):
        self.version = wparser.get_version(obj)
        self.name = name
        self.CAkClass__SetInitialParams = self.DoNothing # _vptr$CAkIndexable + 70, 
        self.CAkClass__SetInitialFxParams = self.DoNothing # _vptr$CAkIndexable + 71 (v135<=), _vptr$IAkEffectSlotsOwner + 70
        self.CAkClass__SetInitialMetadataParams = self.DoNothing #_vptr$IAkEffectSlotsOwner + 71
        self.CAkClass__SetAuxParams = self.DoNothing # _vptr$CAkIndexable + 72 (v135<=), _vptr$IAkEffectSlotsOwner + 72
        self.CAkClass__SetAdvSettingsParams = self.DoNothing # _vptr$CAkIndexable + 73
        self.CAkClass__ReadStateChunk = self.DoNothing # _vptr$CAkStateAware + 14
        self.CAkClass__SetActionParams = self.DoNothing #_vptr$CAkIndexable + 9
        self.CAkClass__SetActionSpecificParams = self.DoNothing #_vptr$CAkIndexable + 10

    def DoNothing(self, obj, cls):
        raise wmodel.ParseError("Callback not set for " + self.name, obj)

    def CAkAction(self, SetActionParams, SetActionSpecificParams):
        self.CAkClass__SetActionParams = SetActionParams
        self.CAkClass__SetActionSpecificParams = SetActionSpecificParams

    def CAkStateAware(self):
        self.CAkClass__ReadStateChunk = wparser.CAkStateAware__ReadStateChunk

    def CAkParamNodeStateAware(self):
        self.CAkStateAware()
        self.CAkClass__ReadStateChunk = wparser.CAkParamNodeStateAware__ReadStateChunk

    def CAkParameterNodeBase(self):
        self.CAkParamNodeStateAware()
        self.CAkClass__SetAuxParams = wparser.CAkParameterNodeBase__SetAuxParams
        self.CAkClass__SetAdvSettingsParams = wparser.CAkParameterNodeBase__SetAdvSettingsParams

    def CAkParameterNode(self):
        self.CAkParameterNodeBase()
        self.CAkClass__SetInitialParams = wparser.CAkParameterNode__SetInitialParams
        self.CAkClass__SetInitialFxParams = wparser.CAkParameterNode__SetInitialFxParams
        self.CAkClass__SetAdvSettingsParams = wparser.CAkParameterNode__SetAdvSettingsParams
        self.CAkClass__SetInitialMetadataParams = wparser.CAkParameterNode__SetInitialMetadataParams
        #120<=
        #self.CAkClass__SetAuxParams = wparser.CAkParameterNode__SetAuxParams

    def CAkBus(self):
        self.CAkParameterNodeBase()
        self.CAkClass__SetInitialParams = wparser.CAkBus__SetInitialParams
        self.CAkClass__SetInitialFxParams = wparser.CAkBus__SetInitialFxParams
        self.CAkClass__SetInitialMetadataParams = wparser.CAkBus__SetInitialMetadataParams

    # ##########

def CAkState__Create(obj):
    #CAkState::Create
    cls = AkClass(obj, CAkState)
    return cls

def CAkSound__Create(obj):
    #CAkSound::Create
    cls = AkClass(obj, CAkSound)
    cls.CAkParameterNode()
    return cls

def CAkAction__Create(obj, actionType):
    #CAkAction::Create

    # giant switch in CAkAction::Create
    # (some don't exist in earlier versions but no apparent type reuse)
    CAkAction_ActionTypes_056 = {
        0x01000: CAkActionStop,
        0x02000: CAkActionPause,
        0x03000: CAkActionResume,
        0x04000: CAkActionPlay,
        0x05000: CAkActionPlayAndContinue,
        0x06000: CAkActionMute,
        0x07000: CAkActionMute,
        0x08000: CAkActionSetPitch,
        0x09000: CAkActionSetPitch,
        0x0A000: CAkActionSetVolume,
        0x0B000: CAkActionSetVolume,
        0x0C000: CAkActionSetLFE,
        0x0D000: CAkActionSetLFE,
        0x0E000: CAkActionSetLPF,
        0x0F000: CAkActionSetLPF,
        0x10000: CAkActionUseState,
        0x11000: CAkActionUseState,
        0x12000: CAkActionSetState,
        0x13000: CAkActionSetGameParameter, #v056
        0x14000: CAkActionSetGameParameter, #v056
        0x20000: CAkActionEvent,
        0x30000: CAkActionEvent,
        0x40000: CAkActionEvent,
        0x50000: CAkActionDuck,
        0x60000: CAkActionSetSwitch,
        0x61000: CAkActionSetRTPC,
        0x70000: CAkActionBypassFX,
        0x80000: CAkActionBypassFX,
        0x90000: CAkActionBreak,
        0xA0000: CAkActionTrigger,
        0xB0000: CAkActionSeek,
    }
    CAkAction_ActionTypes_072 = {
        0x0100: CAkActionStop,
        0x0200: CAkActionPause,
        0x0300: CAkActionResume,
        0x0400: CAkActionPlay,
        0x0500: CAkActionPlayAndContinue, #early (removed in later versions)
        0x0600: CAkActionMute,
        0x0700: CAkActionMute,
        0x0800: CAkActionSetAkProp, #AkPropID_Pitch
        0x0900: CAkActionSetAkProp, #AkPropID_Pitch
        0x0A00: CAkActionSetAkProp, #(none) / AkPropID_Volume (~v145) / AkPropID_FirstRtpc (v150) 
        0x0B00: CAkActionSetAkProp, #(none) / AkPropID_Volume (~v145) / AkPropID_FirstRtpc (v150)
        0x0C00: CAkActionSetAkProp, #AkPropID_BusVolume
        0x0D00: CAkActionSetAkProp, #AkPropID_BusVolume
        0x0E00: CAkActionSetAkProp, #AkPropID_LPF
        0x0F00: CAkActionSetAkProp, #AkPropID_LPF
        0x1000: CAkActionUseState,
        0x1100: CAkActionUseState,
        0x1200: CAkActionSetState,
        0x1300: CAkActionSetGameParameter,
        0x1400: CAkActionSetGameParameter,
        0x1500: CAkActionEvent, #not in v150
        0x1600: CAkActionEvent, #not in v150
        0x1700: CAkActionEvent, #not in v150
        0x1900: CAkActionSetSwitch,
        0x1A00: CAkActionBypassFX,
        0x1B00: CAkActionBypassFX,
        0x1C00: CAkActionBreak,
        0x1D00: CAkActionTrigger,
        0x1E00: CAkActionSeek,
        0x1F00: CAkActionRelease,
        0x2000: CAkActionSetAkProp, #AkPropID_HPF
        0x2100: CAkActionPlayEvent,
        0x2200: CAkActionResetPlaylist,
        0x2300: CAkActionPlayEventUnknown, #normally not defined
        0x3000: CAkActionSetAkProp, #AkPropID_HPF
        0x3100: CAkActionSetFX,
        0x3200: CAkActionSetFX,
        0x3300: CAkActionBypassFX,
        0x3400: CAkActionBypassFX,
        0x3500: CAkActionBypassFX,
        0x3600: CAkActionBypassFX,
        0x3700: CAkActionBypassFX,
    }
    CAkAction_ActionTypes_150_changes = {
        0x1A00: CAkActionBreak,
        0x1B00: CAkActionTrigger,
    }

    version = wparser.get_version(obj)
    if version >= 150:
        CAkAction_ActionTypes_072.update(CAkAction_ActionTypes_150_changes)

    if   version <= 56:
        name = CAkAction_ActionTypes_056.get(actionType & 0xFF000)
    else:
        name = CAkAction_ActionTypes_072.get(actionType & 0xFF00)

    if name is None:
        raise wmodel.ParseError("Unknown action type %05x " % (actionType), obj)

    cls = AkClass(obj, name)

    CAkAction_dispatch = {
        CAkActionStop: (wparser.CAkActionActive__SetActionParams, wparser.CAkActionStop__SetActionSpecificParams),
        CAkActionPause: (wparser.CAkActionActive__SetActionParams, wparser.CAkActionPause__SetActionSpecificParams),
        CAkActionResume: (wparser.CAkActionActive__SetActionParams, wparser.CAkActionResume__SetActionSpecificParams),
        CAkActionPlay: (wparser.CAkActionPlay__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionPlayAndContinue: (wparser.CAkActionPlay__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionMute: (wparser.CAkActionSetValue__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetPitch: (wparser.CAkActionSetValue__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetVolume: (wparser.CAkActionSetValue__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetLFE: (wparser.CAkActionSetValue__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetLPF: (wparser.CAkActionSetValue__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetAkProp: (wparser.CAkActionSetValue__SetActionParams, wparser.CAkActionSetAkProp__SetActionSpecificParams),
        CAkActionUseState: (wparser.CAkAction__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetState: (wparser.CAkActionSetState__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetGameParameter: (wparser.CAkActionSetValue__SetActionParams, wparser.CAkActionSetGameParameter__SetActionSpecificParams),
        CAkActionEvent: (wparser.CAkAction__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionDuck: (wparser.CAkAction__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetSwitch: (wparser.CAkActionSetSwitch__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetRTPC: (wparser.CAkActionSetRTPC__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSetFX: (wparser.CAkActionSetFX__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionBypassFX: (wparser.CAkActionBypassFX__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionBreak: (wparser.CAkAction__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionTrigger: (wparser.CAkAction__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionSeek: (wparser.CAkActionSeek__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionRelease: (wparser.CAkActionRelease__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionPlayEvent: (wparser.CAkActionPlayEvent__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        CAkActionResetPlaylist: (wparser.CAkActionActive__SetActionParams, wparser.CAkActionResetPlaylist__SetActionSpecificParams),
        CAkActionPlayEventUnknown: (wparser.CAkActionPlay__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
    }

    if   cls.version == 26:
        CAkAction_dispatch.update({
            # extends from CAkActionSetLFE (062 from CAkActionSetAkProp and 053 from CAkAction)
            CAkActionSetVolume: (wparser.CAkActionSetValue__SetActionParams, wparser.CAkActionSetAkProp__SetActionSpecificParams),
        })


    if   cls.version == 56:
        CAkAction_dispatch.update({
            # extends from CAkActionSetLFE (062 from CAkActionSetAkProp and 053 from CAkAction)
            CAkActionUseState: (wparser.CAkActionSetValue__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        })

    if   cls.version <= 122:
        CAkAction_dispatch.update({
            CAkActionStop: (wparser.CAkActionActive__SetActionParams, wparser.CAkAction__SetActionSpecificParams),
        })

    dispatch = CAkAction_dispatch.get(cls.name)
    if dispatch:
        cls.CAkAction(*dispatch)
    return cls

def CAkEvent__Create(obj):
    #CAkEvent::Create
    cls = AkClass(obj, CAkEvent)
    return cls

def CAkRanSeqCntr__Create(obj):
    #CAkRanSeqCntr::Create
    cls = AkClass(obj, CAkRanSeqCntr)
    cls.CAkParameterNode()
    return cls

def CAkSwitchCntr__Create(obj):
    #CAkSwitchCntr::Create
    cls = AkClass(obj, CAkSwitchCntr)
    cls.CAkParameterNode()
    return cls

def CAkActorMixer__Create(obj):
    #CAkActorMixer::Create
    cls = AkClass(obj, CAkActorMixer)
    cls.CAkParameterNode()
    return cls

def CAkBus__Create(obj):
    #CAkBus::Create
    cls = AkClass(obj, CAkBus)
    cls.CAkBus()
    return cls

def CAkLayerCntr__Create(obj):
    #CAkLayerCntr::Create
    cls = AkClass(obj, CAkLayerCntr)
    cls.CAkParameterNode()
    return cls

def CAkMusicSegment__Create(obj):
    #CAkMusicSegment::Create
    cls = AkClass(obj, CAkMusicSegment)
    cls.CAkParameterNode()
    return cls

def CAkMusicTrack__Create(obj):
    #CAkMusicTrack::Create
    cls = AkClass(obj, CAkMusicTrack)
    cls.CAkParameterNode()
    return cls

def CAkMusicSwitchCntr__Create(obj):
    #CAkMusicSwitchCntr::Create
    cls = AkClass(obj, CAkMusicSwitchCntr)
    cls.CAkParameterNode()
    return cls

def CAkMusicRanSeqCntr__Create(obj):
    #CAkMusicRanSeqCntr::Create
    cls = AkClass(obj, CAkMusicRanSeqCntr)
    cls.CAkParameterNode()
    return cls

def CAkAttenuation__Create(obj):
    #CAkAttenuation::Create
    cls = AkClass(obj, CAkAttenuation)
    return cls

def CAkDialogueEvent__Create(obj):
    #CAkDialogueEvent::Create
    cls = AkClass(obj, CAkDialogueEvent)
    return cls

def CAkFeedbackNode__Create(obj):
    #CAkFeedbackNode::Create
    cls = AkClass(obj, CAkFeedbackNode)
    cls.CAkParameterNode()
    return cls

def CAkFeedbackBus__Create(obj):
    #CAkFeedbackBus::Create
    cls = AkClass(obj, CAkFeedbackBus)
    cls.CAkBus()
    return cls

def CAkFxShareSet__Create(obj):
    #CAkFxShareSet::Create
    cls = AkClass(obj, CAkFxShareSet)
    cls.CAkStateAware()
    return cls

def CAkFxCustom__Create(obj):
    #CAkFxCustom::Create
    cls = AkClass(obj, CAkFxCustom)
    cls.CAkStateAware()
    return cls

def CAkAuxBus__Create(obj):
    #CAkAuxBus::Create
    cls = AkClass(obj, CAkAuxBus)
    cls.CAkBus()
    return cls

def CAkLFOModulator__Create(obj):
    #CAkLFOModulator::Create
    cls = AkClass(obj, CAkLFOModulator)
    return cls

def CAkEnvelopeModulator__Create(obj):
    #CAkEnvelopeModulator::Create
    cls = AkClass(obj, CAkEnvelopeModulator)
    return cls

def CAkAudioDevice__Create(obj):
    #CAkAudioDevice::Create
    cls = AkClass(obj, CAkAudioDevice)
    cls.CAkStateAware()
    return cls

def CAkTimeModulator__Create(obj):
    #CAkTimeModulator::Create
    cls = AkClass(obj, CAkTimeModulator)
    return cls

def CAkSidechainMixIndexable__Create(obj):
    #CAkSidechainMixIndexable::Create
    cls = AkClass(obj, CAkSidechainMixIndexable)
    return cls


# #############################################################################
# SETUP

# this module was split from wparser so it references functions from it, and wparser in turn
# calls functions here = circular reference. Python <3.7 doesn't seem to support "from x import y"
# circular refs (raises ImportError), so just load module ref indirectly when starting the parser.
def setup():
    global wparser

    # probably not needed since modules are singletons but just in case
    if wparser:
        return

    # load local import and put in var (modules in python are first-class things too)
    from . import wparser as wparser_ref
    wparser = wparser_ref
