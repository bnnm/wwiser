import logging
from . import wdefs

#******************************************************************************
# HIRC: PLUGINS


#AkSineTone (v056>=?)
def CAkFxSrcSineParams__SetParamsBlock(obj, size):
    #CAkFxSrcSineParams::SetParamsBlock
    obj = obj.node('AkSineFXParams')

    obj.f32('fFrequency')
    obj.f32('fGain')
    obj.f32('fDuration')
    obj.U32('uChannelMask').fmt(wdefs.fmt_ch)

#AkSoundEngineDLL (part of main engine)
def CAkFxSrcSilenceParams__SetParamsBlock(obj, size):
    #CAkFxSrcSilenceParams::SetParamsBlock
    obj = obj.node('AkFXSrcSilenceParams')

    obj.f32('fDuration')
    obj.f32('fRandomizedLengthMinus')
    obj.f32('fRandomizedLengthPlus')
    return


#AkToneGen
def CAkToneGenParams__SetParamsBlock(obj, size):
    #CAkToneGenParams::SetParamsBlock
    obj = obj.node('AkToneGenParams')

    obj.f32('fGain')
    obj.f32('fStartFreq')
    obj.f32('fStopFreq')
    obj.f32('fStartFreqRandMin')
    obj.f32('fStartFreqRandMax')
    obj.U8x('bFreqSweep')
    obj.U32('eGenSweep').fmt(wdefs.CAkToneGen__AkToneGenSweep)
    obj.f32('fStopFreqRandMin')
    obj.f32('fStopFreqRandMax')
    obj.U32('eGenType').fmt(wdefs.CAkToneGen__AkToneGenType)
    obj.U32('eGenMode').fmt(wdefs.CAkToneGen__AkToneGenMode)
    obj.f32('fFixDur')
    obj.f32('fAttackDur')
    obj.f32('fDecayDur')
    obj.f32('fSustainDur')
    obj.f32('fSustainVal')
    obj.f32('fReleaseDur')
    if   size == 0x41: #~062<= (065?)
        pass
    elif size == 0x45: #~072>=
        obj.U32('uChannelMask').fmt(wdefs.fmt_ch)

    return


#AkParametricEQ
def CAkParameterEQFXParams__SetParamsBlock(obj, size):
    #CAkParameterEQFXParams::SetParamsBlock
    obj = obj.node('AkParameterEQFXParams') #m_Params

    count = 3
    for elem in obj.list('Band', 'EQModuleParams', count):
        elem.U32('eFilterType').fmt(wdefs.CAkParameterEQ__AkFilterType)
        elem.f32('fGain')
        elem.f32('fFrequency')
        elem.f32('fQFactor')
        elem.U8x('bOnOff')
    obj.f32('fOutputLevel')
    obj.U8x('bProcessLFE')
    return


#AkDelay
def CAkDelayFXParams__SetParamsBlock(obj, size):
    #CAkDelayFXParams::SetParamsBlock
    obj = obj.node('AkDelayFXParams')

    #RTPC: AkDelayRTPCParams
    #NonRTPC: AkDelayNonRTPCParams
    obj.f32('NonRTPC.fDelayTime')
    obj.f32('RTPC.fFeedback')
    obj.f32('RTPC.fWetDryMix')
    obj.f32('RTPC.fOutputLevel') #db
    obj.U8x('RTPC.bFeedbackEnabled')
    if   size == 0x11: #026<=
        pass
    elif size == 0x12:
        obj.U8x('NonRTPC.bProcessLFE')

    return


#AkPeakLimiter
def CAkPeakLimiterFXParams__SetParamsBlock(obj, size):
    #CAkPeakLimiterFXParams::SetParamsBlock
    obj = obj.node('AkPeakLimiterFXParams')

    #RTPC: AkPeakLimiterRTPCParams
    #NonRTPC: AkPeakLimiterNonRTPCParams
    obj.f32('RTPC.fThreshold')
    obj.f32('RTPC.fRatio')
    obj.f32('NonRTPC.fLookAhead')
    obj.f32('RTPC.fRelease')
    obj.f32('RTPC.fOutputLevel') #db
    obj.U8x('NonRTPC.bProcessLFE')
    obj.U8x('NonRTPC.bChannelLink')

    return


#AkMatrixReverb
def CAkFDNReverbFXParams__SetParamsBlock(obj, size):
    #CAkFDNReverbFXParams::SetParamsBlock
    obj = obj.node('AkFDNReverbFXParams')

    #RTPC: AkFDNReverbRTPCParams
    #NonRTPC: AkFDNReverbNonRTPCParams
    obj.f32('RTPC.fReverbTime')
    obj.f32('RTPC.fHFRatio')
    obj.u32('NonRTPC.uNumberOfDelays')
    delays = obj.lastval

    obj.f32('RTPC.fDryLevel') #dB
    obj.f32('RTPC.fWetLevel') #dB
    obj.f32('NonRTPC.fPreDelay') #dB
    obj.U8x('NonRTPC.uProcessLFE')
    obj.U32('NonRTPC.uDelayLengthsMode').fmt(wdefs.CAkFDNReverbFX__AkDelayLengthsMode)
    delay_mode = obj.lastval

    if delay_mode == 1 and delays:
        for _i in range(delays):
            obj.f32('RTPC.fDelayTime')


#AkRoomVerb
def CAkRoomVerbFXParams__SetParamsBlock(obj, size):
    #CAkRoomVerbFXParams::SetParamsBlock
    obj = obj.node('AkStereoDelayFXParams')

    elem = obj.node('RTPCParams') #sRTPCParams
    elem.f32('fDecayTime')
    elem.f32('fHFDamping')
    elem.f32('fDiffusion')
    elem.f32('fStereoWidth')
    elem.f32('fFilter1Gain')
    elem.f32('fFilter1Freq')
    elem.f32('fFilter1Q')
    elem.f32('fFilter2Gain')
    elem.f32('fFilter2Freq')
    elem.f32('fFilter2Q')
    elem.f32('fFilter3Gain')
    elem.f32('fFilter3Freq')
    elem.f32('fFilter3Q')
    elem.f32('fFrontLevel') #db
    elem.f32('fRearLevel') #db
    elem.f32('fCenterLevel') #db
    elem.f32('fLFELevel') #db
    elem.f32('fDryLevel') #db
    elem.f32('fERLevel') #db
    elem.f32('fReverbLevel') #db

    elem = obj.node('InvariantParams') #sInvariantParams
    elem.U8x('bEnableEarlyReflections')
    elem.u32('uERPattern')
    elem.f32('fReverbDelay')
    elem.f32('fRoomSize')
    elem.f32('fERFrontBackDelay')
    elem.f32('fDensity')
    elem.f32('fRoomShape')
    elem.u32('uNumReverbUnits')
    elem.U8x('bEnableToneControls')
    elem.U32('eFilter1Pos').fmt(wdefs.CAkRoomVerbFX__FilterInsertType)
    elem.U32('eFilter1Curve').fmt(wdefs.CAkRoomVerbFX__FilterCurveType)
    elem.U32('eFilter2Pos').fmt(wdefs.CAkRoomVerbFX__FilterInsertType)
    elem.U32('eFilter2Curve').fmt(wdefs.CAkRoomVerbFX__FilterCurveType)
    elem.U32('eFilter3Pos').fmt(wdefs.CAkRoomVerbFX__FilterInsertType)
    elem.U32('eFilter3Curve').fmt(wdefs.CAkRoomVerbFX__FilterCurveType)
    elem.f32('fInputCenterLevel') #db
    elem.f32('fInputLFELevel') #db

    elem = obj.node('AlgorithmTunings') #sAlgoTunings
    elem.f32('fDensityDelayMin')
    elem.f32('fDensityDelayMax')
    elem.f32('fDensityDelayRdmPerc')
    elem.f32('fRoomShapeMin')
    elem.f32('fRoomShapeMax')
    elem.f32('fDiffusionDelayScalePerc')
    elem.f32('fDiffusionDelayMax')
    elem.f32('fDiffusionDelayRdmPerc')
    elem.f32('fDCFilterCutFreq')
    elem.f32('fReverbUnitInputDelay')
    elem.f32('fReverbUnitInputDelayRmdPerc')

    return

#AkFlanger
def CAkFlangerFXParams__SetParamsBlock(obj, size):
    #CAkFlangerFXParams::SetParamsBlock
    obj = obj.node('AkFlangerFXParams')

    #RTPC: AkFlangerRTPCParams
    #NonRTPC: AkFlangerNonRTPCParams
    obj.f32('NonRTPC.fDelayTime')
    obj.f32('RTPC.fDryLevel')
    obj.f32('RTPC.fFfwdLevel')
    obj.f32('RTPC.fFbackLevel')

    obj.f32('RTPC.fModDepth')
    obj.f32('RTPC.modParams.lfoParams.fFrequency')
    obj.U32('RTPC.modParams.lfoParams.eWaveform').fmt(wdefs.CAkFlangerFX__Waveform)
    obj.f32('RTPC.modParams.lfoParams.fSmooth')
    obj.f32('RTPC.modParams.lfoParams.fPWM')

    obj.f32('RTPC.modParams.phaseParams.fPhaseOffset')
    obj.U32('RTPC.modParams.phaseParams.ePhaseMode').fmt(wdefs.CAkFlangerFX__PhaseMode)
    obj.f32('RTPC.modParams.phaseParams.fPhaseSpread')
    obj.f32('RTPC.fOutputLevel') #db
    obj.f32('RTPC.fWetDryMix')
    obj.U8x('NonRTPC.bEnableLFO')
    obj.U8x('NonRTPC.bProcessCenter')
    obj.U8x('NonRTPC.bProcessLFE')

    return

#AkGuitarDistortion
def CAkGuitarDistortionFXParams__SetParamsBlock(obj, size):
    #CAkGuitarDistortionFXParams::SetParamsBlock
    obj = obj.node('AkGuitarDistortionFXParams')

    count = 3
    for elem in obj.list('PreEQ', 'AkFilterBand', count):
        elem.U32('eFilterType').fmt(wdefs.CAkGuitarDistortion__AkFilterType)
        elem.f32('fGain')
        elem.f32('fFrequency')
        elem.f32('fQFactor')
        elem.U8x('bOnOff')
    for elem in obj.list('PostEQ', 'AkFilterBand', count):
        elem.U32('eFilterType').fmt(wdefs.CAkGuitarDistortion__AkFilterType)
        elem.f32('fGain')
        elem.f32('fFrequency')
        elem.f32('fQFactor')
        elem.U8x('bOnOff')

    elem = obj.node('AkDistortionParams')
    elem.U32('eDistortionType').fmt(wdefs.CAkGuitarDistortion__AkDistortionType)
    elem.f32('fDrive')
    elem.f32('fTone')
    elem.f32('fRectification')
    elem.f32('fOutputLevel') #db
    elem.f32('fWetDryMix')

    return


#AkConvolutionReverb
def CAkConvolutionReverbFXParams__SetParamsBlock(obj, size):
    #CAkConvolutionReverbFXParams::SetParamsBlock
    obj = obj.node('AkConvolutionReverbFXParams') #m_Params

    obj.f32('fPreDelay')
    obj.f32('fFrontRearDelay')
    obj.f32('fStereoWidth')

    obj.f32('fInputCenterLevel') #db
    obj.f32('fInputLFELevel') #db
    if   size <= 0x30: #v118<=
        pass
    elif size >= 0x34: #v120>=
        obj.f32('fInputStereoWidth')

    obj.f32('fFrontLevel') #db
    obj.f32('fRearLevel') #db
    obj.f32('fCenterLevel') #db
    obj.f32('fLFELevel') #db
    obj.f32('fDryLevel') #db
    obj.f32('fWetLevel')
    obj.U32('eAlgoType').fmt(wdefs.CAkConvolutionReverbFX__AkConvolutionAlgoType)
    if size >= 0x38: #~v135
        obj.f32('unknown?') #db

    return


#AkSoundEngineDLL
def CAkMeterFXParams__SetParamsBlock(obj, size):
    #CAkMeterFXParams::SetParamsBlock
    obj = obj.node('AkMeterFXParams') #m_Params

    #RTPC: AkMeterRTPCParams
    #NonRTPC: AkMeterNonRTPCParams
    obj.f32('RTPC.fAttack')
    obj.f32('RTPC.fRelease')
    obj.f32('RTPC.fMin')
    obj.f32('RTPC.fMax')
    obj.f32('RTPC.fHold')
    if size == 0x19: #v088<=
        pass
    else:
        obj.U8x('NonRTPC.eMode').fmt(wdefs.CAkMeterFX__AkMeterMode)
    if size <= 0x1A: #v120<=
        pass
    else: #0x1B #v125>=
        obj.U8x('NonRTPC.eScope').fmt(wdefs.CAkMeterFX__AkMeterScope)
    obj.U8x('NonRTPC.bApplyDownstreamVolume')
    obj.U32('NonRTPC.uGameParamID')

    return


#AkStereoDelay
def CAkStereoDelayFXParams__SetParamsBlock(obj, size):
    #CAkStereoDelayFXParams::SetParamsBlock
    obj = obj.node('AkStereoDelayFXParams')

    count = 2
    for elem in obj.list('StereoDelayParams', 'AkStereoDelayChannelParams', count):
        elem.U32('eInputType').fmt(wdefs.CAkStereoDelayFX__AkInputChannelType) #in a separate array but to simplify
        elem.f32('fDelayTime')
        elem.f32('fFeedback') #db
        elem.f32('fCrossFeed') #db
    obj.U32('eFilterType').fmt(wdefs.CAkStereoDelayFX__AkFilterType)

    elem = obj.node('AkStereoDelayFilterParams') #FilterParams
    elem.f32('fFilterGain')
    elem.f32('fFilterFrequency')
    elem.f32('fFilterQFactor')

    obj.f32('fDryLevel') #db
    obj.f32('fWetLevel') #db
    obj.f32('fFrontRearBalance')
    obj.U8x('bEnableFeedback')
    obj.U8x('bEnableCrossFeed')

    return

#AkGain
def CAkGainFXParams__SetParamsBlock(obj, size):
    #CAkGainFXParams::SetParamsBlock
    obj = obj.node('AkGainFXParams')

    obj.f32('fFullbandGain')
    obj.f32('fLFEGain')

    return


#AkSynthOne
def CAkSynthOneParams__SetParamsBlock(obj, size):
    #CAkSynthOneParams::SetParamsBlock
    obj = obj.node('AkSynthOneParams')

    obj.U8x('eFreqMode').fmt(wdefs.CAkSynthOne__AkSynthOneFrequencyMode)
    obj.f32('fBaseFreq')
    obj.U8x('eOpMode').fmt(wdefs.CAkSynthOne__AkSynthOneOperationMode)
    obj.f32('fOutputLevel')
    obj.U8x('eNoiseType').fmt(wdefs.CAkSynthOne__AkSynthOneNoiseType)
    obj.f32('fNoiseLevel')
    obj.f32('fFmAmount')
    obj.U8x('bOverSampling')
    obj.U8x('eOsc1Waveform').fmt(wdefs.CAkSynthOne__AkSynthOneWaveType)
    obj.U8x('bOsc1Invert')
    obj.u32('iOsc1Transpose')
    obj.f32('fOsc1Level')
    obj.f32('fOsc1Pwm')
    obj.U8x('eOsc2Waveform').fmt(wdefs.CAkSynthOne__AkSynthOneWaveType)
    obj.U8x('bOsc2Invert')
    obj.u32('iOsc2Transpose')
    obj.f32('fOsc2Level')
    obj.f32('fOsc2Pwm')

    return


def CAkFxSrcAudioInputParams__SetParamsBlock(obj, size):
    #CAkFxSrcAudioInputParams::SetParamsBlock
    obj = obj.node('AkFXSrcAudioInputParams')

    obj.f32('fGain')

    return


def iZTrashDelayFXParams__SetParamsBlock(obj, size):
    #iZTrashDelayFXParams::SetParamsBlock
    obj = obj.node('iZTrashDelayFXParams')

    obj.f32('fDryOut')
    obj.f32('fWetOut')
    obj.f32('fLowCutoff')
    obj.f32('fLowQ')
    obj.f32('fHighCutoff')
    obj.f32('fHighQ')
    obj.f32('fAmount')
    obj.f32('fFeedback')
    obj.f32('fTrash')
    obj.U32('bHasChanged')

    return

# #############################################################################

plugin_dispatch = {
    0x00640002: CAkFxSrcSineParams__SetParamsBlock,
    0x00650002: CAkFxSrcSilenceParams__SetParamsBlock,
    0x00660002: CAkToneGenParams__SetParamsBlock,
    0x00690003: CAkParameterEQFXParams__SetParamsBlock,
    0x006A0003: CAkDelayFXParams__SetParamsBlock,
    0x006E0003: CAkPeakLimiterFXParams__SetParamsBlock,
    0x00730003: CAkFDNReverbFXParams__SetParamsBlock,
    0x00760003: CAkRoomVerbFXParams__SetParamsBlock,
    0x007D0003: CAkFlangerFXParams__SetParamsBlock,
    0x007E0003: CAkGuitarDistortionFXParams__SetParamsBlock,
    0x007F0003: CAkConvolutionReverbFXParams__SetParamsBlock,
    0x00810003: CAkMeterFXParams__SetParamsBlock,
    0x00870003: CAkStereoDelayFXParams__SetParamsBlock,
    0x008B0003: CAkGainFXParams__SetParamsBlock,
    0x00940002: CAkSynthOneParams__SetParamsBlock,
    0x00C80002: CAkFxSrcAudioInputParams__SetParamsBlock,
    0x00041033: iZTrashDelayFXParams__SetParamsBlock

   #0x00AE0007: (no params)
   #0x00B50007: (no params)
}

def parse_chunk_default(obj, size, params_name):
    obj = obj.node('AkPluginParam')

    # others:
    # - Motion Source (0x01990002): rumble/force feedback config (x8 floats? + u16 count + u16 channels?)
    obj.gap(params_name, size)
    return

def parse_plugin_params(obj, plugin_id, size_name, params_name):
    if not plugin_id or plugin_id < 0:
        return

    # rather than version we check size, since plugins may be updated separatedly,
    # though plugin changes are less common
    #version = get_version(obj)

    # Most plugins are found in separate DLLs/libs, implementing AkPlugin and related interfaces
    # Some of their params use decibel to percent formula: value = pow(10.0, f * 0.050000001), marked as "db"

    obj.U32(size_name)
    size = obj.lastval
    if size == 0:
        return

    #obj = obj.node('AkPluginParam')
    #obj.omax(size) #only works in a subobj, meh

    dispatch = plugin_dispatch.get(plugin_id)
    if dispatch:
        dispatch(obj, size)
    else:
        parse_chunk_default(obj, size, params_name)

    #obj.consume()

    return
