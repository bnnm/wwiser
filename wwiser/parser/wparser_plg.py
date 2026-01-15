from . import wdefs

#******************************************************************************
# HIRC: PLUGINS

def get_version(obj):
    root = obj.get_root()
    return root.get_version()

#AkSineTone (v056>=?)
def CAkFxSrcSineParams__SetParamsBlock(obj, size):
    #CAkFxSrcSineParams::SetParamsBlock
    obj = obj.node('AkSineFXParams')
    obj.omax(size)

    obj.f32('fFrequency')
    obj.f32('fGain')
    obj.f32('fDuration')
    obj.U32('uChannelMask').fmt(wdefs.fmt_ch)

    obj.consume()
    return

#AkSoundEngineDLL (part of main engine)
def CAkFxSrcSilenceParams__SetParamsBlock(obj, size):
    #CAkFxSrcSilenceParams::SetParamsBlock
    obj = obj.node('AkFXSrcSilenceParams')
    obj.omax(size)

    obj.f32('fDuration')
    obj.f32('fRandomizedLengthMinus')
    obj.f32('fRandomizedLengthPlus')

    obj.consume()
    return


#AkToneGen
def CAkToneGenParams__SetParamsBlock(obj, size):
    #CAkToneGenParams::SetParamsBlock
    obj = obj.node('AkToneGenParams')
    obj.omax(size)

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

    obj.consume()
    return


#AkParametricEQ
def CAkParameterEQFXParams__SetParamsBlock(obj, size):
    #CAkParameterEQFXParams::SetParamsBlock
    #CAkParametricEQFXParams::SetParamsBlock #168>=
    obj = obj.node('AkParameterEQFXParams') #m_Params
    obj.omax(size)

    version = get_version(obj)

    if version <= 168:
        count = 3
        for elem in obj.list('Band', 'EQModuleParams', count):
            elem.U32('eFilterType').fmt(wdefs.CAkParameterEQ__AkFilterType)
            elem.f32('fGain')
            elem.f32('fFrequency')
            elem.f32('fQFactor')
            elem.U8x('bOnOff')

        obj.f32('fOutputLevel')
        if version <= 26:
            pass
        else:
            obj.U8x('bProcessLFE')

    elif version <= 169:
        obj.f32('fOutputLevel')
        obj.U8x('bProcessLFE')

        count = 8
        for elem in obj.list('Band', 'EQModuleParams', count):
            elem.U8x('bOnOff')
            elem.U32('gap0') #.fmt(wdefs.CAkParameterEQ__AkFilterType)
            elem.U32('uRolloff')
            elem.f32('fGain')
            elem.f32('fFrequency')
            elem.f32('fQFactor')

    else:
        obj.f32('fOutputGain') #calculated from fOutputLevel
        obj.U8x('bProcessLFE')
        obj.tid('uSidechainId')
        obj.U8x('bSidechainGlobalScope')
        
        obj.U8x('uNumBands')
        count = obj.lastval

        obj.U32('uBandEnabledBitfield')
        obj.U32('uBandDynamicsEnabledBitfield')
        
        for elem in obj.list('Band', 'EQModuleParams', count):
            elem.U8x('gap0') 
            elem.U8x('uBandRolloff')
            elem.f32('fBandFrequency')
            elem.f32('fBandGainDb')
            elem.f32('fBandQFactor')

    obj.consume()
    return


#AkDelay
def CAkDelayFXParams__SetParamsBlock(obj, size):
    #CAkDelayFXParams::SetParamsBlock
    obj = obj.node('AkDelayFXParams')
    obj.omax(size)

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

    obj.consume()
    return


#AkPeakLimiter
def CAkPeakLimiterFXParams__SetParamsBlock(obj, size):
    #CAkPeakLimiterFXParams::SetParamsBlock
    obj = obj.node('AkPeakLimiterFXParams')
    obj.omax(size)

    #RTPC: AkPeakLimiterRTPCParams
    #NonRTPC: AkPeakLimiterNonRTPCParams
    obj.f32('RTPC.fThreshold')
    obj.f32('RTPC.fRatio')
    obj.f32('NonRTPC.fLookAhead')
    obj.f32('RTPC.fRelease')
    obj.f32('RTPC.fOutputLevel') #db
    obj.U8x('NonRTPC.bProcessLFE')
    obj.U8x('NonRTPC.bChannelLink')

    obj.consume()
    return


#AkMatrixReverb
def CAkFDNReverbFXParams__SetParamsBlock(obj, size):
    #CAkFDNReverbFXParams::SetParamsBlock
    obj = obj.node('AkFDNReverbFXParams')
    obj.omax(size)

    version = get_version(obj)

    #RTPC: AkFDNReverbRTPCParams
    #NonRTPC: AkFDNReverbNonRTPCParams
    obj.f32('RTPC.fReverbTime')
    obj.f32('RTPC.fHFRatio')
    if version <= 26:
        obj.u32('unknown')
        delays = 0
    else:
        obj.u32('NonRTPC.uNumberOfDelays')
        delays = obj.lastval

    obj.f32('RTPC.fDryLevel') #dB
    obj.f32('RTPC.fWetLevel') #dB
    obj.f32('NonRTPC.fPreDelay') #dB
    obj.U8x('NonRTPC.uProcessLFE')
    if version <= 26:
        obj.u32('unknown')
        obj.u32('unknown')
        delay_mode = 0
    else:
        obj.U32('NonRTPC.uDelayLengthsMode').fmt(wdefs.CAkFDNReverbFX__AkDelayLengthsMode)
        delay_mode = obj.lastval

    if delay_mode == 1 and delays:
        for _i in range(delays):
            obj.f32('RTPC.fDelayTime')


    obj.consume()
    return


#AkRoomVerb
def CAkRoomVerbFXParams__SetParamsBlock(obj, size):
    #CAkRoomVerbFXParams::SetParamsBlock
    obj = obj.node('AkStereoDelayFXParams')
    obj.omax(size)

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

    obj.consume()
    return


#AkFlanger
def CAkFlangerFXParams__SetParamsBlock(obj, size):
    #CAkFlangerFXParams::SetParamsBlock
    obj = obj.node('AkFlangerFXParams')
    obj.omax(size)

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

    obj.consume()
    return


#AkGuitarDistortion
def CAkGuitarDistortionFXParams__SetParamsBlock(obj, size):
    #CAkGuitarDistortionFXParams::SetParamsBlock
    obj = obj.node('AkGuitarDistortionFXParams')
    obj.omax(size)

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

    obj.consume()
    return


#AkConvolutionReverb
def CAkConvolutionReverbFXParams__SetParamsBlock(obj, size):
    #CAkConvolutionReverbFXParams::SetParamsBlock
    obj = obj.node('AkConvolutionReverbFXParams') #m_Params
    obj.omax(size)

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
    if size >= 0x39: #~v145
        obj.U8x('unknown?') #db

    obj.consume()
    return


#AkSoundEngineDLL
def CAkMeterFXParams__SetParamsBlock(obj, size):
    #CAkMeterFXParams::SetParamsBlock
    obj = obj.node('AkMeterFXParams') #m_Params
    obj.omax(size)

    #RTPC: AkMeterRTPCParams
    #NonRTPC: AkMeterNonRTPCParams
    obj.f32('RTPC.fAttack')
    obj.f32('RTPC.fRelease')
    obj.f32('RTPC.fMin')
    obj.f32('RTPC.fMax')
    obj.f32('RTPC.fHold')
    if size >= 0x1c: #v144>=
        obj.U8x('RTPC.bInfiniteHold')

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
    #TODO: check v172 param names

    obj.consume()
    return


#AkStereoDelay
def CAkStereoDelayFXParams__SetParamsBlock(obj, size):
    #CAkStereoDelayFXParams::SetParamsBlock
    obj = obj.node('AkStereoDelayFXParams')
    obj.omax(size)

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

    obj.consume()
    return


#AkGain
def CAkGainFXParams__SetParamsBlock(obj, size):
    #CAkGainFXParams::SetParamsBlock
    obj = obj.node('AkGainFXParams')
    obj.omax(size)

    obj.f32('fFullbandGain')
    obj.f32('fLFEGain')

    obj.consume()
    return


#AkHarmonizer (v62+, BLands 2)
def CAkHarmonizerFXParams__SetParamsBlock(obj, size):
    #CAkHarmonizerFXParams::SetParamsBlock
    obj = obj.node('AkHarmonizerFXParams')
    obj.omax(size)

    count = 2
    for elem in obj.list('Voice', 'AkPitchVoiceParams', count):
        elem.U8x('bEnable')
        elem.f32('fPitchFactor')
        elem.f32('fGain')

        subelem = elem.node('AkVoiceFilterParams') #Filter
        subelem.U32('eFilterType').fmt(wdefs.CAkHarmonizerFX__AkFilterType_0)
        subelem.f32('fFilterGain')
        subelem.f32('fFilterFrequency')
        subelem.f32('fFilterQFactor')

    obj.U32('eInputType').fmt(wdefs.CAkHarmonizerFX__AkInputType)
    obj.f32('fDryLevel')
    obj.f32('fWetLevel')
    obj.u32('uWindowSize')
    obj.U8x('bProcessLFE')
    obj.U8x('bSyncDry')

    obj.consume()
    return


#AkSynthOne
def CAkSynthOneParams__SetParamsBlock(obj, size):
    #CAkSynthOneParams::SetParamsBlock
    obj = obj.node('AkSynthOneParams')
    obj.omax(size)

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

    obj.consume()
    return


def CAkFxSrcAudioInputParams__SetParamsBlock(obj, size):
    #CAkFxSrcAudioInputParams::SetParamsBlock
    obj = obj.node('AkFXSrcAudioInputParams')
    obj.omax(size)

    obj.f32('fGain')

    obj.consume()
    return


def iZTrashDelayFXParams__SetParamsBlock(obj, size):
    #iZTrashDelayFXParams::SetParamsBlock
    obj = obj.node('iZTrashDelayFXParams')
    obj.omax(size)

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

    obj.consume()
    return

#TODO: missing some fields in later versions? need to test more
def CREVFxSrcModelPlayerParams__SetParamsBlock(obj, size):
    #CREVFxSrcModelPlayerParams::SetParamsBlock
    obj = obj.node('CREVFxSrcModelPlayerParams')
    obj.omax(size)

    obj.f32('unknown')
    obj.f32('unknown')
    obj.f32('unknown')
    obj.f32('unknown')
    obj.f32('unknown')
    obj.f32('unknown')

    elem = obj.node('EngineSimulationControlData')
    elem.s16('EndianStatus')
    elem.u16('SizeOf')
    elem.f32('UpShiftDuration')
    elem.f32('UpShiftAttackDuration')
    elem.f32('UpShiftAttackVolumeSpike')
    elem.f32('UpShiftAttackRPM')
    elem.f32('UpShiftAttackThrottleTime')
    elem.f32('UpShiftWobbleEnabled')
    elem.U32('UpShiftWobblePitchFreq')
    elem.f32('UpShiftWobblePitchAmp')
    elem.f32('UpShiftWobbleVolFreq')
    elem.f32('UpShiftWobbleVolAmp')
    elem.f32('UpShiftWobbleDuration')
    elem.f32('DownShiftDuration')
    elem.f32('PopDuration')
    elem.f32('ClutchRPMSpike')
    elem.f32('ClutchRPMSpikeDuration')
    elem.f32('ClutchRPMMergeTime')

    elem = obj.node('AccelDecelModelControlData')
    elem.s16('DefaultSingleRamp')
    elem.u16('SizeOf')
    elem.f32('DecelVolume_Off')
    elem.f32('DecelVolume_On')
    elem.f32('PopsEnabled')
    elem.f32('PopsVolumeMax')
    elem.f32('PopsVolumeMin')
    elem.f32('PopsFreqMin')
    elem.f32('PopsFreqMax')
    elem.f32('PopsEngineDuck')
    elem.f32('PopRange')
    elem.f32('PopDuration')
    elem.f32('IdleVolume')
    elem.f32('IdleTechnique')
    elem.f32('IdleRampIn')
    elem.f32('IDLE_TECHNIQUE_COVERUP')
    elem.f32('IDLE_TECHNIQUE_RAMPIN')

    obj.consume()
    return

# internal plugins, possibly useful
#SystemSinkParams::SetParamsBlock
#BGMSinkParams::SetParamsBlock
#AkSystemOutputMeta::SetParamsBlock

# #############################################################################

plugin_dispatch_skip_26 = {
    0x00730003 #not all fields have same meaning, too few examples to fix
}


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
    0x008A0003: CAkHarmonizerFXParams__SetParamsBlock,
    0x00940002: CAkSynthOneParams__SetParamsBlock,
    0x00C80002: CAkFxSrcAudioInputParams__SetParamsBlock,
    0x00041033: iZTrashDelayFXParams__SetParamsBlock,
    #0x01A01052: CREVFxSrcModelPlayerParams__SetParamsBlock

   #0x00AE0007: (no params)
   #0x00B50007: (no params)
}

def parse_chunk_default(obj, size, params_name):
    obj = obj.node('AkPluginParam')

    # others:
    # - Motion Source (0x01990002): rumble/force feedback config (x8 floats? + u16 count + u16 channels?)
    obj.gap(params_name, size)
    return

def parse_plugin_params(obj, plugin_id, size_name, params_name, always=False):
    if not plugin_id:
        return
    # early versions have -1 (nothing) but do have empty size/params
    if plugin_id < 0 and not always:
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

    #version = get_version(obj)
    #if version <= 26 and plugin_id in plugin_dispatch_skip_26:
    #    dispatch = None
    #else:
    
    dispatch = plugin_dispatch.get(plugin_id)
    if dispatch:
        dispatch(obj, size)
    else:
        parse_chunk_default(obj, size, params_name)

    #obj.consume()

    return
