import logging
from . import wmodel, wio, wdefs, wparser_cls as wcls, wparser_plg as wplg


# parser mimics AK's functions, naming and some internals as to simplify debugging.
# It's still a representation of the bank, rather than AK's classes, so it doesn't
# try to follow all inheritance stuff (so it's easier to compare with disassembly).
#
# Typically each bank object reads values, sets some global engine defaults, and
# creates/adds a new object to some list/hashmap (while checking no repeats are
# added and other validations). This create new nodes roughly when Wwise uses a new
# class, but often isn't 1:1, since values are moved around (for example multiple
# bank u8 bitflags may end in the same u32, in a different order, in a global
# object rather than where it's read). Similarly some extra nodes are added here
# and there to help understanding usage.
#
# Could go in a Parser class but python 'slef' stuff is annoying


def get_version(obj):
    root = obj.get_root()
    return root.get_version()

def has_feedback(obj):
    root = obj.get_root()
    return root.has_feedback()

# has custom fieldd (not in standard versions)
def is_custom(obj):
    root = obj.get_root()
    return root.is_custom()


#******************************************************************************
# HIRC: COMMON

#helper
def parse_plugin(obj, name='ulPluginID'):
    #actual format is:
    # 16b=plugin id
    # 12b=company id (managed by AK)
    # 4b=plugin type
    fld = obj.U32(name).fmt(wdefs.AkPluginType_id)
    if obj.lastval == -1:
        return

    fld.U16('type',    (obj.lastval >>  0) & 0x000F).fmt(wdefs.AkPluginType)
    fld.U16('company', (obj.lastval >>  4) & 0x03FF).fmt(wdefs.AkPluginType_company)
    #ids can repeat in different companies
    #fld.U16('id',      (obj.lastval >> 16) & 0xFFFF).fmt(wdefs.AkPluginType_id)

    #plugin_id = obj.lastval
    #if plugin_id == 0x01990005 or plugin_id == 0x00640002:
    #    logging.info("parser: found plugin 0x%08X (already parsed)", plugin_id)
    return

#helper
def parse_rtpc_graph(obj, name='pRTPCMgr', subname='AkRTPCGraphPoint'):
    for elem in obj.list(name, 'AkRTPCGraphPoint', obj.lastval):
        elem.f32('From')
        elem.f32('To')
        elem.U32('Interp').fmt(wdefs.AkCurveInterpolation)
    return

#128>=
def AkPropBundle_float_unsigned_short___SetInitialParams(obj, cls):
    #AkPropBundle<float,unsigned short>::SetInitialParams
    #AkPropBundle<float,unsigned short,(AkMemID)0>::SetInitialParams #135
    #AkPropBundleBase<float,unsigned short,(AkMemID)0>::SetInitialParams #150
    obj = obj.node('AkPropBundle<float,unsigned short>') #AkPropBundle

    # despite the generic name this is used by CAkState only
    obj.u16('cProps')
    elems = obj.list('pProps', 'AkPropBundle', obj.lastval).preload()
    for elem in elems:
        elem.U16('pID').fmt(wdefs.AkRTPC_ParameterID) #not a AkPropID (states-params are like mini-RTPCs)
    for elem in elems:
        elem.f32('pValue')

#    count = obj.lastval
#    for i in range(count):
#        obj.U16('pID').fmt(wdefs.AkPropID)
#    for i in range(count):
#        obj.f32('pValue')
    return

#072>= 128<= (062>=?)
def AkPropBundle_float___SetInitialParams(obj, cls):
    #AkPropBundle<float>::SetInitialParams
    obj = obj.node('AkPropBundle<float>') #AkPropBundle

    # despite the generic name this is used by CAkState only
    obj.u8i('cProps')
    elems = obj.list('pProps', 'AkPropBundle', obj.lastval).preload()
    for elem in elems:
        elem.U8x('pID').fmt(wdefs.AkRTPC_ParameterID) #not a AkPropID (states-params are like mini-RTPCs)
    for elem in elems:
        elem.f32('pValue')

#    count = obj.lastval
#    for i in range(count):
#        obj.U8x('pID').fmt(wdefs.AkPropID)
#    for i in range(count):
#        obj.f32('pValue')
    return

#072>= (062>=?)
def AkPropBundle_AkPropValue_unsigned_char___SetInitialParams(obj, cls, modulator=False):
    #AkPropBundle<AkPropValue>::SetInitialParams
    #AkPropBundle<AkPropValue,unsigned char>::SetInitialParams #v128>=
    #AkPropBundle<AkPropValue,unsigned char,(AkMemID)0>::SetInitialParams #v135>=
    #AkPropBundleBase<AkPropValue,unsigned char,(AkMemID)0>::SetInitialParams #v150>=
    #AkPropBundleBase<AkPropValue,unsigned char,(AkMemID)1>::SetInitialParams #v150>=
    obj = obj.node('AkPropBundle<AkPropValue,unsigned char>') #AkPropBundle

    if modulator:
        prop_fmt = wdefs.AkModulatorPropID
        prop_tids = wdefs.AkModulatorPropID_tids
    else:
        prop_fmt = wdefs.AkPropID
        prop_tids = wdefs.AkPropID_tids
    props = []

    obj.u8i('cProps')
    elems = obj.list('pProps', 'AkPropBundle', obj.lastval).preload()
    for elem in elems:
        elem.U8x('pID').fmt(prop_fmt)
        props.append(prop_fmt.get(elem.lastval))

    num = 0
    for elem in elems:
        # unions are autodetected as floats or low ints, but IDs aren't easy to do so
        if props[num] in prop_tids:
            elem.tid('pValue')
        else:
            elem.uni('pValue')

        num += 1

#    count = obj.lastval
#    for i in range(count):
#        obj.U8x('pID').fmt(prop_fmt)
#    for i in range(count):
#        obj.uni('pValue')
    return

#072>= (062>=?)
def AkPropBundle_RANGED_MODIFIERS_AkPropValue__unsigned_char___SetInitialParams(obj, cls, modulator=False):
    #AkPropBundle<RANGED_MODIFIERS<AkPropValue>>::SetInitialParams
    #AkPropBundle<RANGED_MODIFIERS<AkPropValue>,unsigned char>::SetInitialParams #v128>=
    #AkPropBundle<RANGED_MODIFIERS<AkPropValue>,unsigned char,(AkMemID)1>::SetInitialParams #v135>=
    #AkPropBundleBase<RANGED_MODIFIERS<AkPropValue>,unsigned char,(AkMemID)0>::SetInitialParams #v150>=
    #AkPropBundleBase<RANGED_MODIFIERS<AkPropValue>,unsigned char,(AkMemID)1>::SetInitialParams #v150>=
    #AkPropBundleBase<RANGED_MODIFIERS<AkPropValue>,unsigned char,(AkMemID)2>::SetInitialParams #v150>=
    obj = obj.node('AkPropBundle<RANGED_MODIFIERS<AkPropValue>>') #AkPropBundle

    if modulator:
        prop_fmt = wdefs.AkModulatorPropID
    else:
        prop_fmt = wdefs.AkPropID

    obj.u8i('cProps')
    elems = obj.list('pProps', 'AkPropBundle', obj.lastval).preload()
    for elem in elems:
        elem.U8x('pID').fmt(prop_fmt)
    for elem in elems:
        elem.uni('min')
        elem.uni('max')

#    count = obj.lastval
#    for i in range(count):
#        obj.U8x('pID').fmt(prop_fmt)
#    for i in range(count):
#        obj.uni('min')
#        obj.uni('max')
    return

#026>=
def CAkBankMgr__LoadSource(obj, cls, subnode=False):
    #CAkBankMgr::LoadSource
    if not subnode:
        obj = obj.node('AkBankSourceData')

    parse_plugin(obj)
    plugin_id = obj.lastval
    PluginType = (plugin_id & 0x0F)

    if   cls.version <= 89:
        obj.U32('StreamType').fmt(wdefs.AkBank__AKBKSourceType)
    else:
        obj.U8x('StreamType').fmt(wdefs.AkBank__AKBKSourceType)
    stream_type = obj.lastval


    if cls.version <= 46:
        elem = obj.node('AkAudioFormat')
        if cls.version <= 26: #26=TH
            elem.u32('dataIndex') #only used if StreamType is data
            elem.u32('uSampleRate')

            # c=channels, ??=channel related, f=format
            #                    ffff ??         cc 
            # - 00019102 = 000000011001000100000010 = stereo xma
            # - 00018901 = 000000011000100100000001 = mono xma
            # - 00001102 = 000000000001000100000010 = stereo vorbis?
            # - 00000901 = 000000000000100100000001 = mono vorbis?
            # - 000A1201 = 000010100001001000000001 = Wwise Silence
            # - 00021201 = 000000100001001000000001 = Wwise Silence/Tone
            # - 00009102 = 000000001001000100000010 = PCM stereo?
            # - 00008901 = 000000001000100100000001 = PCM mono?
            # - 00010901 = 000000010000100100000001 = ADPCM mono
            # - 00011102 = 000000010001000100000010 = ADPCM stereo
            elem.U32('uFormatBits?')

        else: #36=SM
            elem.u32('uSampleRate')
            elem.U32('uFormatBits') \
                .bit('uChannelMask', elem.lastval, 0, 0x3FFFF) \
                .bit('uBitsPerSample', elem.lastval, 18, 0x3F) \
                .bit('uBlockAlign', elem.lastval, 24, 0x1F) \
                .bit('uTypeID', elem.lastval, 29, 0x3) \
                .bit('uInterleaveID', elem.lastval, 31)
    else:
        pass

    elem = obj.node('AkMediaInformation')
    elem.tid('sourceID').fnv(wdefs.fnv_no)

    if cls.version <= 26:
        pass
    elif cls.version <= 88:
        elem.tid('uFileID') #wem or bnk
        if stream_type != 1: #memory/prefetch
            elem.U32('uFileOffset')
            elem.U32('uInMemoryMediaSize')

    elif cls.version <= 89:
        elem.tid('uFileID') #wem or bnk
        if stream_type != 1: #memory/prefetch
            elem.U32('uFileOffset')
        elem.U32('uInMemoryMediaSize') #assumed

    elif cls.version <= 112:
        elem.tid('uFileID') #wem or bnk
        if stream_type != 2: #memory/prefetch
            elem.U32('uFileOffset')
        elem.U32('uInMemoryMediaSize')

    elif cls.version <= 150:
        #fileID is sourceID
        elem.U32('uInMemoryMediaSize')

    else:
        elem.U32('cacheID')
        elem.U32('uInMemoryMediaSize')


    if   cls.version <= 26:
        pass
    elif cls.version <= 112: #recheck
        elem.U8x('uSourceBits') \
            .bit('bIsLanguageSpecific', elem.lastval,0) \
            .bit('bHasSource', elem.lastval,1) \
            .bit('bExternallySupplied', elem.lastval,2)
    else:
        elem.U8x('uSourceBits') \
            .bit('bIsLanguageSpecific', elem.lastval,0) \
            .bit('bPrefetch', elem.lastval,1) \
            .bit('bNonCachable', elem.lastval, 3) \
            .bit('bHasSource', elem.lastval, 7)

    if cls.version <= 26:
        has_param = True #(PluginType == 2) #technically checks 2 but always has size
        always_param = True
    elif cls.version <= 126:
        has_param = (PluginType == 2 or PluginType == 5)
        always_param = False
    else:
        has_param = (PluginType == 2)
        always_param = False

    if has_param:
        wplg.parse_plugin_params(obj, plugin_id,  'uSize', 'pParam', always=always_param)
        #obj.U32('uSize')
        #obj.gap('pParam', obj.lastval)
    return

#046>=
def CAkParameterNode__SetAdvSettingsParams(obj, cls):
    #CAkParameterNode::SetAdvSettingsParams
    obj = obj.node('AdvSettingsParams')

    if   cls.version <= 36: #36=UFC
        #fields seem correct based on common values and comparing 34=SM's BE/LE bnks
        obj.U32('eVirtualQueueBehavior').fmt(wdefs.AkVirtualQueueBehavior)
        obj.U8x('bKillNewest') #MaxReachedBehavior
        obj.u16('u16MaxNumInstance')
        obj.U32('eBelowThresholdBehavior').fmt(wdefs.AkBelowThresholdBehavior)
        obj.U8x('bIsMaxNumInstOverrideParent')
        obj.U8x('bIsVVoicesOptOverrideParent')

    elif cls.version <= 53: #44=AC2
        obj.U8x('eVirtualQueueBehavior').fmt(wdefs.AkVirtualQueueBehavior)
        obj.U8x('bKillNewest') #MaxReachedBehavior
        obj.u16('u16MaxNumInstance')
        obj.U8x('eBelowThresholdBehavior').fmt(wdefs.AkBelowThresholdBehavior)
        obj.U8x('bIsMaxNumInstOverrideParent')
        obj.U8x('bIsVVoicesOptOverrideParent')

    elif cls.version <= 89: #56=KOF13
        obj.U8x('eVirtualQueueBehavior').fmt(wdefs.AkVirtualQueueBehavior)
        obj.U8x('bKillNewest') #MaxReachedBehavior
        obj.U8x('bUseVirtualBehavior') #OverLimitBehavior
        obj.u16('u16MaxNumInstance')
        obj.U8x('bIsGlobalLimit')
        obj.U8x('eBelowThresholdBehavior').fmt(wdefs.AkBelowThresholdBehavior)
        obj.U8x('bIsMaxNumInstOverrideParent') #ucMaxNumInstOverrideParent v056
        obj.U8x('bIsVVoicesOptOverrideParent') #ucVVoicesOptOverrideParent v056
        if cls.version <= 72:
            pass
        else:
            obj.U8x('bOverrideHdrEnvelope')
            obj.U8x('bOverrideAnalysis')
            obj.U8x('bNormalizeLoudness')
            obj.U8x('bEnableEnvelope')
    else:
        obj.U8x('byBitVector') \
           .bit('bKillNewest', obj.lastval, 0) \
           .bit('bUseVirtualBehavior', obj.lastval, 1) \
           .bit('bIgnoreParentMaxNumInst', obj.lastval, 3) \
           .bit('bIsVVoicesOptOverrideParent', obj.lastval, 4)
        obj.U8x('eVirtualQueueBehavior').fmt(wdefs.AkVirtualQueueBehavior)
        obj.u16('u16MaxNumInstance')
        obj.U8x('eBelowThresholdBehavior').fmt(wdefs.AkBelowThresholdBehavior)
        obj.U8x('byBitVector') \
           .bit('bOverrideHdrEnvelope', obj.lastval, 0) \
           .bit('bOverrideAnalysis', obj.lastval, 1) \
           .bit('bNormalizeLoudness', obj.lastval, 2) \
           .bit('bEnableEnvelope', obj.lastval, 3)

    return

#026>=
def CAkParameterNode__SetInitialFxParams(obj, cls):
    #CAkParameterNode::SetInitialFxParams
    obj = obj.node('NodeInitialFxParams')

    obj.U8x('bIsOverrideParentFX') #when != 0

    if cls.version <= 26:
        obj.u32('uNumFx')
        count = 0
        if obj.lastval != 0: #flag
            count = 1
    else:
        obj.u8i('uNumFx')
        count = obj.lastval

    if count > 0:
        if   cls.version <= 26:
            pass
        elif   cls.version <= 145:
            obj.U8x('bitsFXBypass')
        else:
            obj.U8x('bBypassAll')

        for elem in obj.list('pFXChunk', 'FXChunk', count):
            if   cls.version <= 26:
                pass
            else:
                elem.u8i('uFXIndex')

            elem.tid('fxID') #.fnv(wdefs.fnv_sfx) #tid in 113=Doom16
            plugin_id = elem.lastval

            if   cls.version <= 26:
                elem.U8x('bitsFXBypass')
                elem.U8x('bIsRendered')
                wplg.parse_plugin_params(elem, plugin_id, 'ulSize', 'pDataBloc', always=True)
                #elem.U32('ulSize')
                #elem.gap('pDataBloc', elem.lastval)

            elif cls.version <= 48:
                elem.U8x('bIsRendered')
                wplg.parse_plugin_params(elem, plugin_id, 'ulPresetSize', 'pDataBloc', always=True)
                #elem.U32('ulPresetSize')
                #elem.gap('pDataBloc', elem.lastval)

            elif cls.version <= 145:
                elem.U8x('bIsShareSet')
                elem.U8x('bIsRendered')

            else:
                elem.U8x('bitVector') \
                    .bit('bBypass', obj.lastval, 0) \
                    .bit('bShareSet', obj.lastval, 1) \
                    .bit('bRendered', obj.lastval, 2)

            if   cls.version <= 46:
                pass
            elif cls.version <= 48:
                elem.u32('ulNumBankData')
                for elem2 in elem.list('pParams', 'Plugin', elem.lastval):
                    elem2.U32('FXParameterSetID') #plugin? (not seen)
                    elem2.U32('item')
            else:
                pass

    return

#046>=
def CAkParameterNode__SetInitialParams(obj, cls):
    #CAkParameterNode::SetInitialParams
    obj = obj.node('NodeInitialParams')

    if cls.version <= 38: #38=KOF12
        obj.f32('Volume') #VolumeMain #f32
        obj.f32('Volume.min')
        obj.f32('Volume.max')
        obj.f32('LFE') #LFEVolumeMain #f32
        obj.f32('LFE.min')
        obj.f32('LFE.max')
        obj.s32('Pitch')#PitchMain #s32
        obj.s32('Pitch.min') #s32
        obj.s32('Pitch.max') #s32
        obj.s32('LPF')#LPFMain
        obj.s32('LPF.min')
        obj.s32('LPF.max')

    elif cls.version <= 56: #44=AC2
        #RANGED_MODIFIERS<float>
        obj.f32('Volume') #VolumeMain
        obj.f32('Volume.min')
        obj.f32('Volume.max')
        obj.f32('LFE') #LFEVolumeMain
        obj.f32('LFE.min')
        obj.f32('LFE.max')
        obj.f32('Pitch')#PitchMain
        obj.f32('Pitch.min')
        obj.f32('Pitch.max')
        obj.f32('LPF')#LPFMain
        obj.f32('LPF.min')
        obj.f32('LPF.max')

    else: #62=Blands2
        AkPropBundle_AkPropValue_unsigned_char___SetInitialParams(obj, cls)

        AkPropBundle_RANGED_MODIFIERS_AkPropValue__unsigned_char___SetInitialParams(obj, cls)


    if cls.version <= 52:
        obj.tid('ulStateGroupID').fnv(wdefs.fnv_var)
    else:
        pass

    return

#-
def CAkParameterNodeBase__SetAdvSettingsParams(obj, cls):
    #CAkParameterNodeBase::SetAdvSettingsParams
    raise wmodel.ParseError("dummy virtual function", obj)

#125>=
def CAkParameterNodeBase__SetAuxParams(obj, cls):
    #CAkParameterNodeBase::SetAuxParams
    obj = obj.node('AuxParams')

    if cls.version <= 89:
        obj.U8x('bOverrideGameAuxSends')
        obj.U8x('bUseGameAuxSends')
        obj.U8x('bOverrideUserAuxSends')
        obj.U8x('bHasAux')
        has_aux = obj.lastval != 0
    else:
        obj.U8x('byBitVector') \
           .bit('bOverrideUserAuxSends', obj.lastval, 2) \
           .bit('bHasAux', obj.lastval, 3) \
           .bit('bOverrideReflectionsAuxBus', obj.lastval, 4) # bHasAux in v122, > 135
        has_aux = (obj.lastval >> 3) & 1

    if has_aux:
        for _i in range(4):
            obj.tid('auxID')

    if cls.version <= 134:
        pass
    elif cls.version <= 135 and is_custom(obj):
        pass
    else:
        obj.tid('reflectionsAuxBus')
    return

#072>= 120<=
def CAkParameterNode__SetAuxParams(obj, cls):
    #CAkParameterNode::SetAuxParams

    #same code, should be called by callbacks
    CAkParameterNodeBase__SetAuxParams(obj, cls)
    return

#046>=
def CAkParentNode_CAkParameterNode___SetChildren(obj, cls):
    #CAkParentNode<CAkParameterNode>::SetChildren
    obj = obj.node('Children')

    obj.u32('ulNumChilds')
    #for elem in obj.list('mapChild', 'WwiseObject', obj.lastval):
    for _i in range(obj.lastval):
        obj.tid('ulChildID').fnv(wdefs.fnv_no)
    return

#125>=
def CAkStateAware__ReadStateChunk(obj, cls):
    #CAkStateAware::ReadStateChunk
    obj = obj.node('StateChunk')

    obj.var('ulNumStateProps')
    for elem in obj.list('stateProps', 'AkStatePropertyInfo', obj.lastval):
        elem.var('PropertyId').fmt(wdefs.AkRTPC_ParameterID) #not a AkPropID (states-params are like mini-RTPCs)
        elem.U8x('accumType').fmt(wdefs.AkRtpcAccum)
        if   cls.version <= 126:
            pass
        else:
            elem.U8x('inDb') #bool

    obj.var('ulNumStateGroups')
    for elem in obj.list('pStateChunks', 'AkStateGroupChunk', obj.lastval):
        elem.tid('ulStateGroupID').fnv(wdefs.fnv_var)
        if cls.version <= 154:
            pass
        else:
            elem.tid('ulGroupUsageID').fnv(wdefs.fnv_var)
        elem.U8x('eStateSyncType').fmt(wdefs.AkSyncType)
        elem.var('ulNumStates')
        for elem2 in elem.list('pStates', 'AkState', elem.lastval):
            elem2.tid('ulStateID').fnv(wdefs.fnv_val)
            
            if   cls.version <= 145: #uses AkState
                elem2.tid('ulStateInstanceID').fnv(wdefs.fnv_no)
            else:
                #AkSortedPropBundle_float_unsigned_short___SetInitialParams > AkPropBundleBase_float_unsigned_short___SetInitialParams
                AkPropBundle_float_unsigned_short___SetInitialParams(elem2, cls)
    return

#053>= 120<=
def CAkParameterNodeBase__ReadStateChunk(obj, cls):
    #CAkParameterNodeBase::ReadStateChunk
    obj = obj.node('StateChunk')

    obj.u32('ulNumStateGroups')
    for elem in obj.list('pStateChunks', 'AkStateGroupChunk', obj.lastval):
        elem.tid('ulStateGroupID').fnv(wdefs.fnv_var)
        elem.U8x('eStateSyncType').fmt(wdefs.AkSyncType)
        elem.u16('ulNumStates')
        for elem2 in elem.list('pStates', 'AkState', elem.lastval):
            elem2.tid('ulStateID').fnv(wdefs.fnv_val)
            elem2.tid('ulStateInstanceID').fnv(wdefs.fnv_no)
    return

#128>=
def CAkParamNodeStateAware__ReadStateChunk(obj, cls):
    #CAkParamNodeStateAware::ReadStateChunk
    CAkStateAware__ReadStateChunk(obj, cls)
    return

#026>= 125<=
def CAkParameterNodeBase__ReadFeedbackInfo(obj, cls):
    #CAkParameterNodeBase::ReadFeedbackInfo

    if cls.version <= 26:
        # TODO not in some versions, no apparent flag (Too Human = never, KetnetKick 2 = always)
        if has_feedback(obj): #use fake flag for now
            obj = obj.node('FeedbackInfo')
            obj.U32('uSize')
            size = obj.lastval
            if size: # and has_feedback(obj): #?
                count = size // 0x04
                for _i in range(count):
                    obj.tid('unknown') #must be an ID, not seen

    else:
        if has_feedback(obj): #CAkBankMgr::BankHasFeedback
            obj = obj.node('FeedbackInfo')
            obj.tid('BusId').fnv(wdefs.fnv_bus) #unused in 112>=

            if cls.version <= 56:
                if obj.lastval != 0:
                    obj.f32('fFeedbackVolume')
                    obj.f32('fFeedbackModifierMin')
                    obj.f32('fFeedbackModifierMax')
                    obj.f32('fFeedbackLPF')
                    obj.f32('fFeedbackLPFModMin')
                    obj.f32('fFeedbackLPFModMax')
            else:
                pass

    if cls.version <= 26:
        if has_feedback(obj): #use fake flag for now
            obj.f32('unknown')
    else:
        pass

    return

#046>=
def SetInitialRTPC_CAkParameterNodeBase_(obj, cls, modulator=False):
    #CAkParameterNodeBase::SetInitialRTPC #113<=
    #SetInitialRTPC<CAkParameterNodeBase>
    #AK::RTPC::ReadRtpcCurves<CAkParameterNodeBase> #144>=
    obj = obj.node('InitialRTPC')

    if cls.version <= 36: #36=UFC
        obj.u32('ulNumRTPC')
    elif cls.version <= 141: #38=KOF12
        obj.u16('ulNumRTPC')
    else: #
        obj.u16('uNumCurves')

    for elem in obj.list('pRTPCMgr', 'RTPC', obj.lastval):
        if   cls.version <= 36: #36=UFC
            parse_plugin(elem, 'FXID')
        elif cls.version <= 48: #44=AC2
            parse_plugin(elem, 'FXID')
            elem.U8x('_bIsRendered') #unused
        else:
            pass

        elem.tid('RTPCID').fnv(wdefs.fnv_gmx) #depends on target (ex. gamevar=hashname, rtpc=hashname, modulator=guidname)

        if   cls.version <= 89:
            pass
        else:
            elem.U8x('rtpcType').fmt(wdefs.AkRtpcType) #gap0 in later versions
            elem.U8x('rtpcAccum').fmt(wdefs.AkRtpcAccum) #gap0 in later versions

        if   cls.version <= 89:
            elem.U32('ParamID').fmt(wdefs.AkRTPC_ParameterID)
        elif cls.version <= 113:
            elem.U8x('ParamID').fmt(wdefs.AkRTPC_ParameterID)
        else:
            if modulator:
                param_fmt = wdefs.AkRTPC_ModulatorParamID
            else:
                param_fmt = wdefs.AkRTPC_ParameterID
            elem.var('ParamID').fmt(param_fmt)

        elem.sid('rtpcCurveID')

        if cls.version <= 36: #36=UFC
            elem.U32('eScaling').fmt(wdefs.AkCurveScaling)
            elem.u32('ulSize')
        else: #44=AC2
            elem.U8x('eScaling').fmt(wdefs.AkCurveScaling) #gap0 in later versions
            elem.u16('ulSize')
        parse_rtpc_graph(elem) #indirectly in _vptr$CAkIndexable + 63
    return

#for all sub-RTPCs SDK code is copy-pasted (not call'd), except it sets the RTPC on the bus/layer/etc
def SetInitialRTPC_CAkBus_(obj, cls):
    #CAkParameterNodeBase::SetInitialRTPC #113<=
    #SetInitialRTPC<CAkBus>
    #AK::RTPC::ReadRtpcCurves<CAkBus> #144>=
    SetInitialRTPC_CAkParameterNodeBase_(obj, cls)
    return
def SetInitialRTPC_CAkLayer_(obj, cls):
    #CAkLayer::SetInitialRTPC #113<=
    #SetInitialRTPC<CAkLayer>
    #AK::RTPC::ReadRtpcCurves<CAkLayer> #144>=
    SetInitialRTPC_CAkParameterNodeBase_(obj, cls)
    return
def SetInitialRTPC_CAkAttenuation_(obj, cls):
    #SetInitialRTPC<CAkAttenuation>
    #AK::RTPC::ReadRtpcCurves<CAkAttenuation> #144>=
    SetInitialRTPC_CAkParameterNodeBase_(obj, cls)
    return
def SetInitialRTPC_CAkFxBase_(obj, cls):
    #SetInitialRTPC<CAkFxBase>
    #AK::RTPC::ReadRtpcCurves<CAkFxBase> #144>=
    SetInitialRTPC_CAkParameterNodeBase_(obj, cls)
    return
def SetInitialRTPC_CAkModulator_(obj, cls):
    #SetInitialRTPC<CAkModulator>
    #AK::RTPC::ReadRtpcCurves<CAkModulator> #144>=
    SetInitialRTPC_CAkParameterNodeBase_(obj, cls, modulator=True)
    return

#046>=
def CAkParameterNodeBase__SetNodeBaseParams(obj, cls):
    #CAkParameterNodeBase::SetNodeBaseParams
    obj = obj.node('NodeBaseParams')

    cls.CAkClass__SetInitialFxParams(obj, cls) #_vptr$CAkIndexable + 71 (v135<=), _vptr$IAkEffectSlotsOwner + 70
    
    if   cls.version <= 136:
        pass
    else:
        cls.CAkClass__SetInitialMetadataParams(obj, cls) #_vptr$IAkEffectSlotsOwner + 71

    if   cls.version <= 89:
        pass
    elif cls.version <= 145:
        obj.U8x('bOverrideAttachmentParams')
    else:
        pass

    obj.tid('OverrideBusId').fnv(wdefs.fnv_bus)
    obj.tid('DirectParentID').fnv(wdefs.fnv_no)

    if   cls.version <= 56:
        obj.u8i('ucPriority')
        obj.u8i('bPriorityOverrideParent')
        obj.u8i('bPriorityApplyDistFactor')
        obj.s8i('iDistOffset')
    elif cls.version <= 89:
        obj.U8x('bPriorityOverrideParent')
        obj.U8x('bPriorityApplyDistFactor')
    else:
        obj.U8x('byBitVector') \
           .bit('bPriorityOverrideParent', obj.lastval, 0) \
           .bit('bPriorityApplyDistFactor', obj.lastval, 1) \
           .bit('bOverrideMidiEventsBehavior', obj.lastval, 2) \
           .bit('bOverrideMidiNoteTracking', obj.lastval, 3) \
           .bit('bEnableMidiNoteTracking', obj.lastval, 4) \
           .bit('bIsMidiBreakLoopOnNoteOff', obj.lastval, 5)


    cls.CAkClass__SetInitialParams(obj, cls)


    if   cls.version <= 122:
        CAkParameterNode__SetPositioningParams(obj, cls) #callback, but only possible value
    else:
        CAkParameterNodeBase__SetPositioningParams(obj, cls)

    if   cls.version <= 65: #65=DmC
        pass
    else:
        cls.CAkClass__SetAuxParams(obj, cls)


    cls.CAkClass__SetAdvSettingsParams(obj, cls)


    if   cls.version <= 52: #similar to ReadStateChunk but inline'd
        sub = obj.node('StateChunk') #not in original code but a bit hard to understand otherwise

        if cls.version <= 36: #36=UFC, 34=SM
            #TODO upper bits maybe others? (0/1/0x1E/0x21/0x28/0x31/0x32/0x37/etc)
            sub.U32('eStateSyncType?').fmt(wdefs.AkSyncType)
            sub.u32('ulNumStates')
        else: #44=AC2
            #todo upper bits maybe others? (0x25 found in Wwise demos 046, 0x18 in Enslaved)
            sub.U8x('eStateSyncType').fmt(wdefs.AkSyncType)
            sub.u16('ulNumStates')

        for elem in sub.list('pStates', 'AKBKStateItem', sub.lastval):
            elem.tid('ulStateID').fnv(wdefs.fnv_val)
            elem.U8x('bIsCustom')
            elem.tid('ulStateInstanceID').fnv(wdefs.fnv_no)

    elif cls.version <= 122:
        CAkParameterNodeBase__ReadStateChunk(obj, cls)

    elif cls.version <= 126:
        CAkStateAware__ReadStateChunk(obj, cls)

    else:
        cls.CAkClass__ReadStateChunk(obj, cls) #_vptr$CAkStateAware + 14 (same thing though)


    SetInitialRTPC_CAkParameterNodeBase_(obj, cls)


    if   cls.version <= 126:
        CAkParameterNodeBase__ReadFeedbackInfo(obj, cls)
    else:
        pass

    return

#046>=
def CAkParameterNodeBase__SetPositioningParams(obj, cls):
    #CAkParameterNodeBase::SetPositioningParams
    obj = obj.node('PositioningParams')

    # we reuse this function though, see below
    #if cls.version <= 122:
    #    raise wmodel.ParseError("dummy virtual function", obj)

    #todo 3dPositioning bits depends on version
    #cbPositioningInfoOverrideParent older
    if cls.version <= 122:
        fld = obj.U8x('uByVector')
    else:
        fld = obj.U8x('uBitsPositioning')

    fld.bit('bPositioningInfoOverrideParent', obj.lastval, 0)
    if cls.version <= 89:
        fld.bit('bHasListenerRelativeRouting', obj.lastval, 1) #has_3d?  (TODO)
        pass
    elif cls.version <= 112:
        fld.bit('bHasListenerRelativeRouting', obj.lastval, 1) #has_3d?  (TODO)
        fld.bit('unknown2d_next_flag', obj.lastval, 2) #flag for next bit
        fld.bit('unknown2d', obj.lastval, 3) #bPriorityOverrideParent? bIsFXOverrideParent?
        fld.bit('unknown3d', obj.lastval, 4)
        fld.bit('unknown3d', obj.lastval, 5)
        fld.bit('unknown3d', obj.lastval, 6) #always set?
        fld.bit('unknown3d', obj.lastval, 7) #always set?
    elif cls.version <= 122:
        fld.bit('unknown2d_next_flag', obj.lastval, 1) #flag for next bit
        fld.bit('unknown2d', obj.lastval, 2) #bPriorityOverrideParent? bIsFXOverrideParent?
        fld.bit('cbIs3DPositioningAvailable', obj.lastval, 3)
    elif cls.version <= 129:
        fld.bit('unknown2d', obj.lastval, 1) #?
        fld.bit('unknown2d_next_flag', obj.lastval, 2) #flag for next bit
        fld.bit('unknown2d', obj.lastval, 3) #bPriorityOverrideParent? bIsFXOverrideParent?
        fld.bit('cbIs3DPositioningAvailable', obj.lastval, 4)
    else:
        fld.bit('bHasListenerRelativeRouting', obj.lastval, 1) #has_3d?  (TODO)
        fld.bit('ePannerType', obj.lastval, 2, mask=3, fmt=wdefs.AkSpeakerPanningType)
        fld.bit('e3DPositionType', obj.lastval, 5, mask=3, fmt=wdefs.Ak3DPositionType)
    uBitsPositioning = obj.lastval
    has_positioning = (uBitsPositioning >> 0) & 1 #override parent

    has_3d = False
    if has_positioning:
        if cls.version <= 56: #56=KOF13
            #BaseGenParams
            obj.s32('uCenterPct')
            obj.f32('fPAN_RL')
            obj.f32('fPAN_FR')
        else:
            pass

        if cls.version <= 72:
            obj.U8x('cbIs3DPositioningAvailable')
            has_3d = obj.lastval
            if not has_3d:
                obj.U8x('bIsPannerEnabled') #part of BaseGenParams
        elif cls.version <= 89:
            obj.U8x('cbIs2DPositioningAvailable')
            has_2d = obj.lastval
            obj.U8x('cbIs3DPositioningAvailable')
            has_3d = obj.lastval
            if has_2d:
                obj.U8x('bPositioningEnablePanner')
        elif cls.version <= 122:
            has_3d = (uBitsPositioning >> 3) & 1
        elif cls.version <= 129:
            has_3d = (uBitsPositioning >> 4) & 1
        else:
            has_3d = (uBitsPositioning >> 1) & 1

    if has_positioning and has_3d:
        #Gen3DParams
        if   cls.version <= 89:
            obj.U32('eType').fmt(wdefs.AkPositioningType)
            eType = obj.lastval
            uBits3d = 0
        else:
            fld = obj.U8x('uBits3d')
            eType = 0
            uBits3d = obj.lastval

            #todo bit meanings may vary more in older versions
            if   cls.version <= 126:
                fld.bit('eSpatializationMode', obj.lastval, 0, mask=1, fmt=wdefs.Ak3DSpatializationMode)
            else:
                fld.bit('eSpatializationMode', obj.lastval, 0, mask=3, fmt=wdefs.Ak3DSpatializationMode)
            if   cls.version <= 132:
                fld.bit('bHoldEmitterPosAndOrient', obj.lastval, 3)
                fld.bit('bHoldListenerOrient', obj.lastval, 4)
            elif cls.version <= 134:
                fld.bit('bEnableAttenuation', obj.lastval, 3)
                fld.bit('bHoldEmitterPosAndOrient', obj.lastval, 4)
                fld.bit('bHoldListenerOrient', obj.lastval, 5)
                fld.bit('bIsNotLooping?', obj.lastval, 7) #from tests
            else:
                fld.bit('bEnableAttenuation', obj.lastval, 3)
                fld.bit('bHoldEmitterPosAndOrient', obj.lastval, 4)
                fld.bit('bHoldListenerOrient', obj.lastval, 5)
                fld.bit('bEnableDiffraction', obj.lastval, 6)

        if   cls.version <= 89:
            obj.tid('uAttenuationID')
            obj.U8x('bIsSpatialized')
        elif cls.version <= 129:
            obj.tid('uAttenuationID')
        else:
            pass

        if   cls.version <= 72:
            #eType = eType
            has_automation = (eType == 2) #Ak3DUserDef
            has_dynamic = (eType == 3) #Ak3DGameDef
        elif cls.version <= 89:
            eType = (eType >> 0) & 3
            has_automation = (eType != 1)
            has_dynamic = not has_automation
        elif cls.version <= 122:
            e3DPositionType = (uBits3d >> 0) & 3
            has_automation = (e3DPositionType != 1)
            has_dynamic = False
        elif cls.version <= 126:
            e3DPositionType = (uBits3d >> 4) & 1
            has_automation = (e3DPositionType != 1)
            has_dynamic = False
        elif cls.version <= 129:
            e3DPositionType = (uBits3d >> 6) & 1
            has_automation = (e3DPositionType != 1)
            has_dynamic = False
        else:
            e3DPositionType = (uBitsPositioning >> 5) & 3
            has_automation = (e3DPositionType != 0) #(3d == 1 or 3d != 1 and 3d == 2)
            has_dynamic = False


        if has_dynamic:
            obj.U8x('bIsDynamic')

        if has_automation:
            if   cls.version <= 89:
                obj.U32('ePathMode').fmt(wdefs.AkPathMode)
                obj.U8x('bIsLooping')
                obj.s32('TransitionTime')
                if cls.version <= 36: #36=UFC (transition+vertices+items+params ok)
                    pass
                else:
                    obj.U8x('bFollowOrientation')
            else:
                obj.U8x('ePathMode').fmt(wdefs.AkPathMode)
                obj.s32('TransitionTime')

            obj.u32('ulNumVertices')
            for elem in obj.list('pVertices', 'AkPathVertex', obj.lastval):
                elem.f32('Vertex.X')
                elem.f32('Vertex.Y')
                elem.f32('Vertex.Z')
                elem.s32('Duration')

            obj.u32('ulNumPlayListItem')
            for elem in obj.list('pPlayListItems', 'AkPathListItemOffset', obj.lastval):
                elem.U32('ulVerticesOffset')
                elem.u32('iNumVertices')

            #if cls.version <= 36: #36=UFC
            if cls.version <= 36: #36=UFC
                pass
            #38=unknown, KOF13 doesn't use automation
            else:  #44=AC2 (rest of data seems to match offsets but usually all 0s, so it's hard to say)
                for elem in obj.list('Params', 'Ak3DAutomationParams', obj.lastval):
                    elem.f32('fXRange')
                    elem.f32('fYRange')
                    if   cls.version <= 89:
                        pass
                    else:
                        elem.f32('fZRange')

    return

#120<=
def CAkParameterNode__SetPositioningParams(obj, cls):
    #CAkParameterNode::SetPositioningParams

    #has all code from above rather than call'd
    CAkParameterNodeBase__SetPositioningParams(obj, cls)
    return

#140>=
def CAkParameterNode__SetInitialMetadataParams(obj, cls):
    #CAkParameterNode::SetInitialMetadataParams

    obj.U8x('bIsOverrideParentMetadata')
    
    obj.u8i('uNumFx')
    count = obj.lastval

    if count > 0:
        for elem in obj.list('pFXChunk', 'FXChunk', count):
            elem.u8i('uFXIndex')
            elem.tid('fxID') #.fnv(wdefs.fnv_sfx)
            elem.U8x('bIsShareSet')
    return

#140>=
def CAkEffectSlots__SetInitialValues(obj, cls):
    #CAkEffectSlots::SetInitialValues
    #AkOwnedEffectSlots::SetInitialValues #v150
    
    obj.u8i('uNumFx')
    count = obj.lastval

    if count > 0:
        if   cls.version <= 145:
            obj.U8x('bitsFXBypass') #bIsBypassed & 0x11 != 0
        else:
            obj.U8x('bBypassAll')

        for elem in obj.list('pFXChunk', 'FXChunk', count):
            elem.u8i('uFXIndex')
            elem.tid('fxID') #.fnv(wdefs.fnv_sfx)

            if   cls.version <= 145:
                elem.U8x('bIsShareSet')
                elem.U8x('_bIsRendered') #unused (effects can't render)
            else:
                elem.U8x('bitVector') \
                    .bit('bBypass', obj.lastval, 0) \
                    .bit('bShareSet', obj.lastval, 1)

    return

#******************************************************************************
# HIRC: State

#026>= 145<=
def CAkState__SetInitialValues(obj, cls):
    #CAkState::SetInitialValues
    obj = obj.node('StateInitialValues')

    if   cls.version <= 56:
        elem = obj.node('AkStdParameters')
        elem.f32('Volume')
        elem.f32('LFEVolume')
        elem.f32('Pitch')
        elem.f32('LPF')
        if cls.version <= 52:
            elem.U8x('eVolumeValueMeaning').fmt(wdefs.AkValueMeaning)
            elem.U8x('eLFEValueMeaning').fmt(wdefs.AkValueMeaning)
            elem.U8x('ePitchValueMeaning').fmt(wdefs.AkValueMeaning)
            elem.U8x('eLPFValueMeaning').fmt(wdefs.AkValueMeaning)
        else:
            pass

    elif cls.version <= 126:
        AkPropBundle_float___SetInitialParams(obj, cls)
    else:
        AkPropBundle_float_unsigned_short___SetInitialParams(obj, cls)
    return

#-
def CAkBankMgr__ReadState(obj):
    #CAkBankMgr::ReadState
    #CAkBankMgr::StdBankRead<CAkState,CAkState> #144>= (but also has leftover CAkBankMgr::ReadState)
    cls = wcls.CAkState__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulStateID').fnv(wdefs.fnv_no)

    CAkState__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Sound

#026>=
def CAkSound__SetInitialValues(obj, cls):
    #CAkSound::SetInitialValues
    obj = obj.node('SoundInitialValues')

    CAkBankMgr__LoadSource(obj, cls)

    CAkParameterNodeBase__SetNodeBaseParams(obj, cls)

    if cls.version <= 56:
        obj.s16('Loop')
        obj.s16('LoopMod.min')
        obj.s16('LoopMod.max')
    else:
        pass

    return

#-
def CAkBankMgr__ReadSourceParent_CAkSound_(obj):
    #CAkBankMgr::ReadSourceParent<CAkSound>
    cls = wcls.CAkSound__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkSound__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Event Action

#046>=
def CAkActionExcept__SetExceptParams(obj, cls):
    #CAkAction::SetExceptParams #053/056, same but prints error if list size is set
    #CAkActionExcept::SetExceptParams
    obj = obj.node('ExceptParams')

    if cls.version <= 122:
        obj.u32('ulExceptionListSize')
    else:
        obj.var('ulExceptionListSize')

    for elem in obj.list('listElementException', 'WwiseObjectIDext', obj.lastval):
        elem.tid('ulID')
        if cls.version <= 65: #65=ZoE HD
            pass
        else:
            elem.U8x('bIsBus')
    return

#046>=
def CAkAction__SetActionSpecificParams(obj, cls):
    #CAkAction::SetActionSpecificParams
    if cls.version <= 56:
        obj = obj.node('ActionSpecificParams')
        obj.gap('_reserved', 0x10)
    else:
        pass
    return

#046>=
def CAkActionPause__SetActionSpecificParams(obj, cls):
    #CAkActionPause::SetActionSpecificParams
    obj = obj.node('PauseActionSpecificParams')

    if   cls.version <= 56:
        obj.U32('b32IsMaster')
        obj.gap('_reserved', 0x0C)
    elif cls.version <= 62:
        obj.U8x('bIsMaster')
    else:
        obj.U8x('byBitVector') \
           .bit('bIncludePendingResume', obj.lastval, 0) \
           .bit('bApplyToStateTransitions', obj.lastval, 1) \
           .bit('bApplyToDynamicSequence', obj.lastval, 2)
    return

#113>=
def CAkActionResetPlaylist__SetActionSpecificParams(obj, cls):
    #CAkActionResetPlaylist::SetActionSpecificParams
    return

#046>=
def CAkActionResume__SetActionSpecificParams(obj, cls):
    #CAkActionResume::SetActionSpecificParams
    obj = obj.node('ResumeActionSpecificParams')

    if   cls.version <= 56:
        obj.U32('b32IsMaster')
        obj.gap('_reserved', 0x0C)
    elif cls.version <= 62:
        obj.U8x('bIsMaster')
    else:
        obj.U8x('byBitVector') \
           .bit('bIsMasterResume', obj.lastval, 0) \
           .bit('bApplyToStateTransitions', obj.lastval, 1) \
           .bit('bApplyToDynamicSequence', obj.lastval, 2)
    return

#046>=
def CAkActionSetAkProp__SetActionSpecificParams(obj, cls):
    #CAkActionSetPitch::SetActionSpecificParams #056<=
    #CAkActionSetVolume::SetActionSpecificParams #056<=
    #CAkActionSetLFE::SetActionSpecificParams #056<=
    #CAkActionSetLPF::SetActionSpecificParams #056<=
    # *in v056 there is one ::SetActionSpecificParams per subtype but are all the same
    #CAkActionSetGameParameter::SetActionSpecificParams #062<=
    #CAkActionSetAkProp::SetActionSpecificParams #072>=
    obj = obj.node('AkPropActionSpecificParams')

    if cls.version <= 56:
        obj.U32('eValueMeaning').fmt(wdefs.AkValueMeaning)
    else:
        obj.U8x('eValueMeaning').fmt(wdefs.AkValueMeaning)

    for elem in [obj.node('RandomizerModifier')]: #rModifier / RANGED_PARAMETER<float>
        elem.f32('base')#TargetValue.base
        elem.f32('min') #TargetValue.mod.max
        elem.f32('max') #TargetValue.mod.min

    # assumed
    if cls.version <= 26:
        elem.f32('unknown')
    else:
        pass

    return

#056>=
def CAkActionSetGameParameter__SetActionSpecificParams(obj, cls):
    #CAkActionSetGameParameter::SetActionSpecificParams
    obj = obj.node('GameParameterActionSpecificParams')

    if cls.version <= 89:
        pass
    else:
        obj.U8x('bBypassTransition') #when != 0

    if cls.version <= 56:
        obj.U32('eValueMeaning').fmt(wdefs.AkValueMeaning)
    else:
        obj.U8x('eValueMeaning').fmt(wdefs.AkValueMeaning)

    for elem in [obj.node('RANGED_PARAMETER<float>')]: #rModifier / RandomizerModifier
        elem.f32('base')
        elem.f32('min')
        elem.f32('max')
    return

#125>=
def CAkActionStop__SetActionSpecificParams(obj, cls):
    #CAkActionStop::SetActionSpecificParams
    obj = obj.node('StopActionSpecificParams')

    obj.U8x('byBitVector') \
       .bit('bApplyToStateTransitions', obj.lastval, 1) \
       .bit('bApplyToDynamicSequence', obj.lastval, 2)
    return

#046>=
def CAkAction__SetActionParams(obj, cls):
    #CAkAction::SetActionParams
    #obj = obj.node('DefaultActionParams')
    return

#046>=
def CAkActionActive__SetActionParams(obj, cls):
    #CAkActionActive::SetActionParams
    obj = obj.node('ActiveActionParams')

    if cls.version <= 56:
        obj.s32('TTime')
        obj.s32('TTimeMin')
        obj.s32('TTimeMax')
    else:
        pass

    obj.U8x('byBitVector') \
       .bit('eFadeCurve', obj.lastval, 0, mask=0x1F, fmt=wdefs.AkCurveInterpolation)

    cls.CAkClass__SetActionSpecificParams(obj, cls) #_vptr$CAkIndexable + 10

    CAkActionExcept__SetExceptParams(obj, cls)
    return

#150>=
def CAkActionSetFX__SetActionParams(obj, cls):
    #CAkActionSetFX::SetActionParams
    obj = obj.node('SetFXActionParams')

    obj.U8x('bIsAudioDeviceElement')
    obj.U8x('uSlotIndex')
    obj.tid('uFXID')
    obj.U8x('bIsShared')

    CAkActionExcept__SetExceptParams(obj, cls)
    return

#046>=
def CAkActionBypassFX__SetActionParams(obj, cls):
    #CAkActionBypassFX::SetActionParams
    obj = obj.node('BypassFXActionParams')

    obj.U8x('bIsBypass')
    if   cls.version <= 26:
        pass
    elif cls.version <= 145:
        obj.U8x('uTargetMask')
    else:
        obj.U8x('byFxSlot')

    CAkActionExcept__SetExceptParams(obj, cls)
    return

#046>=
def CAkActionPlay__SetActionParams(obj, cls):
    #CAkActionPlay::SetActionParams
    obj = obj.node('PlayActionParams')

    if cls.version <= 56:
        obj.s32('TTime')
        obj.s32('TTimeMin')
        obj.s32('TTimeMax')
    else:
        pass

    obj.U8x('byBitVector') \
       .bit('eFadeCurve', obj.lastval, 0, mask=0x1F, fmt=wdefs.AkCurveInterpolation)

    if cls.version <= 56:
        cls.CAkClass__SetActionSpecificParams(obj, cls)

        CAkActionExcept__SetExceptParams(obj, cls)
    else:
        pass

    if   cls.version <= 26:
        pass
    elif cls.version <= 126:
        obj.tid('fileID').fnv(wdefs.fnv_bnk) #same as bankID
    else:
        obj.tid('bankID').fnv(wdefs.fnv_bnk)

    if cls.version >= 144:
        obj.U32('bankType').fmt(wdefs.AkBankTypeEnum)

    return

#113>=
def CAkActionPlayEvent__SetActionParams(obj, cls):
    #CAkActionPlayEvent::SetActionParams
    #obj = obj.node('PlayEventActionParams')
    return

#112>=
def CAkActionRelease__SetActionParams(obj, cls):
    #CAkActionRelease::SetActionParams
    #obj = obj.node('ReleaseActionParams')
    return

#046>=
def CAkActionSetRTPC__SetActionParams(obj, cls):
    #CAkActionSetRTPC::SetActionParams
    #named differently 056>=?
    obj = obj.node('RTPCActionParams')

    obj.tid('RTPC_ID').fnv(wdefs.fnv_gmx) #depends on target (ex. gamevar=hashname, rtpc=hashname, modulator=guidname)
    obj.f32('fRTPCValue')
    return

#048>=
def CAkActionSeek__SetActionParams(obj, cls):
    #CAkActionSeek::SetActionParams
    obj = obj.node('SeekActionParams')

    obj.U8x('bIsSeekRelativeToDuration') #when > 0
    for elem in [obj.node('RandomizerModifier')]: #rModifier / RANGED_PARAMETER<float>
        elem.f32('fSeekValue')
        elem.f32('fSeekValueMin')
        elem.f32('fSeekValueMax')
    obj.U8x('bSnapToNearestMarker') #when > 0

    CAkActionExcept__SetExceptParams(obj, cls)
    return

#046>=
def CAkActionSetState__SetActionParams(obj, cls):
    #CAkActionSetState::SetActionParams
    obj = obj.node('StateActionParams')

    obj.tid('ulStateGroupID').fnv(wdefs.fnv_var)
    obj.tid('ulTargetStateID').fnv(wdefs.fnv_val)
    return

#046>=
def CAkActionSetSwitch__SetActionParams(obj, cls):
    #CAkActionSetSwitch::SetActionParams
    obj = obj.node('SwitchActionParams')

    obj.tid('ulSwitchGroupID').fnv(wdefs.fnv_var)
    obj.tid('ulSwitchStateID').fnv(wdefs.fnv_val)
    return

#046>=
def CAkActionSetValue__SetActionParams(obj, cls):
    #CAkActionSetValue::SetActionParams
    obj = obj.node('ValueActionParams')

    if cls.version <= 56:
        obj.s32('TTime')
        obj.s32('TTimeMin')
        obj.s32('TTimeMax')
    else:
        pass

    obj.U8x('byBitVector') \
       .bit('eFadeCurve', obj.lastval, 0, mask=0x1F, fmt=wdefs.AkCurveInterpolation)

    cls.CAkClass__SetActionSpecificParams(obj, cls) #_vptr$CAkIndexable + 10

    CAkActionExcept__SetExceptParams(obj, cls)
    return

#026>=
def CAkAction__SetInitialValues(obj, cls):
    #CAkAction::SetInitialValues
    obj = obj.node('ActionInitialValues')

    if   cls.version <= 56:
        obj.tid('ulTargetID')
        obj.s32('tDelay')
        obj.s32('tDelayMin')
        obj.s32('tDelayMax')
        obj.U32('ulSubSectionSize')
        if obj.lastval > 0:
            cls.CAkClass__SetActionParams(obj, cls)

    else:
        if cls.version <= 65: #65=DmC
            obj.tid('ulTargetID')
        else:
            # meaning of idExt:
            #CAkAction::SetElementID = ulElementID, bIsBus
            #CAkActionEvent::SetElementID: ulTargetEventID
            # in CAkActionSetState meaning is a variable value (hashname)
            obj.tid('idExt')

            obj.U8x('idExt_4') \
               .bit('bIsBus', obj.lastval, 0)

        AkPropBundle_AkPropValue_unsigned_char___SetInitialParams(obj, cls)

        AkPropBundle_RANGED_MODIFIERS_AkPropValue__unsigned_char___SetInitialParams(obj, cls)

        cls.CAkClass__SetActionParams(obj, cls)

    return

#-
def CAkBankMgr__ReadAction(obj):
    #CAkBankMgr::ReadAction
    #set_name below

    obj.sid('ulID').fnv(wdefs.fnv_no)

    if get_version(obj) <= 56:
        obj.U32('ulActionType').fmt(wdefs.AkActionType)
    else: #62=Blands2
        obj.U16('ulActionType').fmt(wdefs.AkActionType)

    cls = wcls.CAkAction__Create(obj, obj.lastval)
    obj.set_name(cls.name)

    CAkAction__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Event Sequence

#026>=
def CAkEvent__SetInitialValues(obj, cls):
    #CAkEvent::SetInitialValues
    obj = obj.node('EventInitialValues')

    if cls.version <= 154:
        pass
    else:
        obj.U8x('gap20_0')
        obj.u16('instanceLimit')
        obj.f32('cooldownTime')

    if cls.version <= 122:
        obj.u32('ulActionListSize')
    else:
        obj.var('ulActionListSize')

    for elem in obj.list('actions', 'Action', obj.lastval):
        elem.tid('ulActionID').fnv(wdefs.fnv_no)
    return

#-
def CAkBankMgr__ReadEvent(obj):
    #CAkBankMgr::ReadEvent
    #CAkBankMgr::StdBankRead<CAkEvent,CAkEvent> #144>= (but also has leftover CAkBankMgr::ReadEvent)
    #CAkBankMgr::StdBankRead<CAkEvent> #~154>=
    cls = wcls.CAkEvent__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_evt)

    CAkEvent__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Random/Sequence Container

#026>=
def CAkRanSeqCntr__SetPlaylistWithoutCheck(obj, cls):
    #CAkRanSeqCntr::SetPlaylistWithoutCheck
    #CAkRanSeqCntr::SetPlaylistNoCheck #168 >=
    obj = obj.node('CAkPlayList') #pPlayList

    if cls.version <= 38: #38=KOF12
        obj.u32('ulPlayListItem')
    else:
        obj.u16('ulPlayListItem')

    for elem in obj.list('pItems', 'AkPlaylistItem', obj.lastval):
        elem.tid('ulPlayID').fnv(wdefs.fnv_no)
        if cls.version <= 56:
            elem.u8i('ucWeight')
        else:
            elem.s32('weight') #also u32 in v128

    return

#026>=
def CAkRanSeqCntr__SetInitialValues(obj, cls):
    #CAkRanSeqCntr::SetInitialValues
    obj = obj.node('RanSeqCntrInitialValues')

    CAkParameterNodeBase__SetNodeBaseParams(obj, cls)

    obj.u16('sLoopCount')

    if cls.version <= 72:
        pass
    else:
        obj.u16('sLoopModMin')
        obj.u16('sLoopModMax')

    if cls.version <= 38: #36=USB, 38=KOF13
        obj.s32('TransitionTime')
        obj.s32('TransitionTimeModMin')
        obj.s32('TransitionTimeModMax')
    else:
        obj.f32('fTransitionTime')
        obj.f32('fTransitionTimeModMin')
        obj.f32('fTransitionTimeModMax')

    obj.u16('wAvoidRepeatCount')

    if   cls.version <= 35: #35=JS
        pass
    elif cls.version <= 36: #36=UFC
        obj.u16('unknown') #related to wAvoidRepeatCount (why this version only?)
    else:
        pass

    if cls.version <= 44: #44=DLPO/ME2/AC2
        #AoT2 buggy banks need this, see bank loading info
        if obj.get_root().get_subversion() == 45:
            obj.U16('unknown')
        pass
    elif cls.version <= 45: #45=AoT2
        # same thing
        if obj.get_root().get_subversion() == 45:
            obj.U16('unknown') #unrelated to wAvoidRepeatCount (00/01/03/05)
        pass
    else:
        pass

    if cls.version <= 36: #36=UFC
        obj.U8x('eTransitionMode').fmt(wdefs.AkTransitionMode)
        obj.U8x('eRandomMode').fmt(wdefs.AkRandomMode)
        obj.U8x('eMode').fmt(wdefs.AkContainerMode)
    else:
        obj.U8x('eTransitionMode').fmt(wdefs.AkTransitionMode)
        obj.U8x('eRandomMode').fmt(wdefs.AkRandomMode)
        obj.U8x('eMode').fmt(wdefs.AkContainerMode)

    if   cls.version <= 89:
        obj.U8x('_bIsUsingWeight') #unused
        obj.U8x('bResetPlayListAtEachPlay')
        obj.U8x('bIsRestartBackward')
        obj.U8x('bIsContinuous')
        obj.U8x('bIsGlobal')
    else:
        obj.U8x('byBitVector') \
            .bit('_bIsUsingWeight', obj.lastval, 0) \
            .bit('bResetPlayListAtEachPlay', obj.lastval, 1) \
            .bit('bIsRestartBackward', obj.lastval, 2) \
            .bit('bIsContinuous', obj.lastval, 3) \
            .bit('bIsGlobal', obj.lastval, 4)

    CAkParentNode_CAkParameterNode___SetChildren(obj, cls)

    CAkRanSeqCntr__SetPlaylistWithoutCheck(obj, cls)

    return

#-
def CAkBankMgr__StdBankRead_CAkRanSeqCntr_CAkParameterNodeBase_(obj):
    #CAkBankMgr::StdBankRead<CAkRanSeqCntr,CAkParameterNodeBase>
    #CAkBankMgr::StdBankRead<CAkRanSeqCntr>
    cls = wcls.CAkRanSeqCntr__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkRanSeqCntr__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Switch Container

#026>=
def CAkSwitchCntr__SetInitialValues(obj, cls):
    #CAkSwitchCntr::SetInitialValues
    obj = obj.node('SwitchCntrInitialValues')

    CAkParameterNodeBase__SetNodeBaseParams(obj, cls)

    if cls.version <= 89:
        obj.U32('eGroupType').fmt(wdefs.AkGroupType)
    else:
        obj.U8x('eGroupType').fmt(wdefs.AkGroupType)
    obj.tid('ulGroupID').fnv(wdefs.fnv_var) #ulSwitchGroup ~062<=
    obj.tid('ulDefaultSwitch').fnv(wdefs.fnv_val)
    obj.U8x('bIsContinuousValidation') #!=0

    CAkParentNode_CAkParameterNode___SetChildren(obj, cls)

    obj.u32('ulNumSwitchGroups')
    for elem in obj.list('SwitchList', 'CAkSwitchPackage', obj.lastval):
        elem.sid('ulSwitchID').fnv(wdefs.fnv_val)
        elem.u32('ulNumItems')
        elem2 = elem.node('NodeList')
        for _i in range(elem.lastval):
            elem2.tid('NodeID').fnv(wdefs.fnv_no) #just 'ID'

    obj.u32('ulNumSwitchParams')
    for elem in obj.list('rParams', 'AkSwitchNodeParams', obj.lastval):
        elem.tid('ulNodeID').fnv(wdefs.fnv_no)

        if cls.version <= 89:
            elem.U8x('bIsFirstOnly')
            elem.U8x('bContinuePlayback')
            elem.U32('eOnSwitchMode').fmt(wdefs.AkOnSwitchMode)
        elif cls.version <= 150:
            elem.U8x('byBitVector') \
                .bit('bIsFirstOnly', elem.lastval, 0) \
                .bit('bContinuePlayback', elem.lastval, 1)
            elem.U8x('byBitVector') \
                .bit('eOnSwitchMode', elem.lastval, 0, 0x7, fmt=wdefs.AkOnSwitchMode)
        elif cls.version <= 154:
            elem.U8x('byBitVector') \
                .bit('bIsFirstOnly', elem.lastval, 0) \
                .bit('bContinuePlayback', elem.lastval, 1)
        else:
            elem.U8x('byBitVector') \
                .bit('bIsFirstOnly', elem.lastval, 0) \
                .bit('bContinueAcrossSwitch', elem.lastval, 1)

        elem.s32('FadeOutTime')
        elem.s32('FadeInTime')

    return

#-
def CAkBankMgr__StdBankRead_CAkSwitchCntr_CAkParameterNodeBase_(obj):
    #CAkBankMgr::StdBankRead<CAkSwitchCntr,CAkParameterNodeBase>
    #CAkBankMgr::StdBankRead<CAkSwitchCntr>
    cls = wcls.CAkSwitchCntr__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkSwitchCntr__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Actor-Mixer

#046>=
def CAkActorMixer__SetInitialValues(obj, cls):
    #CAkActorMixer::SetInitialValues
    obj = obj.node('ActorMixerInitialValues')

    CAkParameterNodeBase__SetNodeBaseParams(obj, cls)

    CAkParentNode_CAkParameterNode___SetChildren(obj, cls)
    return

#-
def CAkBankMgr__StdBankRead_CAkActorMixer_CAkParameterNodeBase_(obj):
    #CAkBankMgr::StdBankRead<CAkActorMixer,CAkParameterNodeBase>
    #CAkBankMgr::StdBankRead<CAkActorMixer>
    cls = wcls.CAkActorMixer__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkActorMixer__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Audio Bus

#140>=
def CAkBus__SetInitialMetadataParams(obj, cls):
    #CAkBus::SetInitialMetadataParams
    
    obj.u8i('uNumFx')
    count = obj.lastval

    if count > 0:
        for elem in obj.list('pFXChunk', 'FXChunk', count):
            elem.u8i('uFXIndex')
            elem.tid('fxID') #.fnv(wdefs.fnv_sfx)
            elem.U8x('bIsShareSet')
    return

#046>=
def CAkBus__SetInitialFxParams(obj, cls):
    #CAkBus::SetInitialFxParams > AkOwnedEffectSlots::SetInitialValues
    obj = obj.node('BusInitialFxParams')

    if   cls.version <= 26:
        obj.u32('uNumFx')
        count = 0
        if obj.lastval != 0: #flag
            count = 1
    elif cls.version <= 135:
        obj.u8i('uNumFx')
        count = obj.lastval
    else: #136+
        count = 0

    if cls.version <= 48:
        read_fx = count > 0
    elif cls.version <= 65: #52=WW, 65=DmC
        read_fx = count > 0 or cls.is_environmental
    else:
        read_fx = count > 0

    if read_fx:
        if   cls.version <= 26:
            pass
        else:
            obj.U8x('bitsFXBypass') #bIsBypassed & 0x11 != 0

        for elem in obj.list('pFXChunk', 'FXChunk', count):
            if   cls.version <= 26:
                parse_plugin(elem, name='fxID') #obj.U32('fxID')
                plugin_id = elem.lastval

            elif cls.version <= 48:
                elem.u8i('uFXIndex')
                parse_plugin(elem, name='fxID') #obj.U32('fxID')
                plugin_id = elem.lastval

            else:
                elem.u8i('uFXIndex')
                elem.tid('fxID') #.fnv(wdefs.fnv_sfx) #tid in 113=Doom16

            if   cls.version <= 26:
                elem.U8x('bitsFXBypass') #bIsBypassed & 0x11 != 0
                elem.U8x('_bIsRendered') #unused
                wplg.parse_plugin_params(elem, plugin_id, 'ulSize', 'pDataBloc', always=True)
                #elem.U32('ulSize')
                #elem.gap('pDataBloc', elem.lastval)

            elif cls.version <= 48:
                elem.U8x('_bIsRendered') #unused
                wplg.parse_plugin_params(elem, plugin_id, 'ulSize', 'pDataBloc', always=True)
                #elem.U32('ulSize')
                #elem.gap('pDataBloc', elem.lastval)

            else:
                elem.U8x('bIsShareSet') #!=0, bIsRendered is earlier versions
                elem.U8x('_bIsRendered') #unused (buses can't render effects)


            if   cls.version <= 46:
                pass
            elif cls.version <= 48:
                elem.u32('ulNumBankData')
                for elem2 in elem.list('pParams', 'Plugin', elem.lastval):
                    elem2.tid('FXParameterSetID') #plugin? (not seen)
                    elem2.U32('item')
            else:
                pass

    if cls.version <= 135:
        pass
    else: #136+
        CAkEffectSlots__SetInitialValues(obj, cls) #like the above fx reading though
        #AkOwnedEffectSlots::SetInitialValues

    if   cls.version <= 89:
        pass
    elif cls.version <= 145:
        obj.tid('fxID_0')
        obj.U8x('bIsShareSet_0') #!=0
    else:
        pass

    return

#026>=
def CAkBus__SetInitialParams(obj, cls):
    #CAkBus::SetInitialParams
    obj = obj.node('BusInitialParams')

    if cls.version <= 56:
        pass
    else:
        AkPropBundle_AkPropValue_unsigned_char___SetInitialParams(obj, cls)

    if cls.version <= 122:
        pass
    else:
        CAkParameterNodeBase__SetPositioningParams(obj, cls)
        cls.CAkClass__SetAuxParams(obj, cls) #_vptr$CAkIndexable + 72 (v135<=), _vptr$IAkEffectSlotsOwner + 72

    if   cls.version <= 53:
        obj.f32('VolumeMain')
        obj.f32('LFEVolumeMain')
        obj.f32('PitchMain')
        obj.f32('LPFMain')

        obj.U8x('bKillNewest')
        obj.U16('u16MaxNumInstance')
        obj.U8x('bIsMaxNumInstOverrideParent')

        if cls.version <= 48:
            pass
        else:
            obj.U16('uChannelConfig').fmt(wdefs.fmt_ch)

        obj.U8x('_unused') #bPriorityApplyDistFactor?
        obj.U8x('_unused') #bPriorityOverrideParent?

        if cls.version <= 48:
            pass
        else:
            obj.U8x('bIsEnvironmental')
            cls.is_environmental = obj.lastval #save for CAkBus::SetInitialFxParams

    elif  cls.version <= 56:
        obj.f32('VolumeMain')
        obj.f32('LFEVolumeMain')
        obj.f32('PitchMain')
        obj.f32('LPFMain')

        obj.U8x('bKillNewest')
        obj.U8x('bUseVirtualBehavior')

        obj.U16('u16MaxNumInstance')
        obj.U8x('bIsMaxNumInstOverrideParent')
        obj.U16('uChannelConfig').fmt(wdefs.fmt_ch)

        obj.U8x('_unused') #EnableWiiCompressor?
        obj.U8x('_unused') #EnableWiiCompressor?
        obj.U8x('bIsEnvBus')
        cls.is_environmental = obj.lastval #save for CAkBus::SetInitialFxParams

    elif cls.version <= 65: #DmC
        obj.U8x('bKillNewest')
        obj.U8x('bUseVirtualBehavior')

        obj.U16('u16MaxNumInstance')
        obj.U8x('bIsMaxNumInstOverrideParent')
        obj.U16('uChannelConfig').fmt(wdefs.fmt_ch)

        obj.U8x('_unused')
        obj.U8x('_unused')
        obj.U8x('bIsEnvBus')
        cls.is_environmental = obj.lastval #save for CAkBus::SetInitialFxParams

    elif cls.version <= 77:
        obj.U8x('bKillNewest') #MaxReachedBehavior
        obj.U8x('bUseVirtualBehavior') #OverLimitBehavior

        obj.U16('u16MaxNumInstance')
        obj.U8x('bIsMaxNumInstOverrideParent')
        obj.U16('uChannelConfig').fmt(wdefs.fmt_ch)

        obj.U8x('_unused')
        obj.U8x('_unused')

    elif cls.version <= 89:
        obj.U8x('bPositioningEnabled')
        obj.U8x('bPositioningEnablePanner')
        obj.U8x('bKillNewest') #MaxReachedBehavior
        obj.U8x('bUseVirtualBehavior') #OverLimitBehavior

        obj.U16('u16MaxNumInstance')
        obj.U8x('bIsMaxNumInstOverrideParent')
        obj.U16('uChannelConfig').fmt(wdefs.fmt_ch)

        obj.U8x('_unused')
        obj.U8x('_unused')
        obj.U8x('bIsHdrBus')
        obj.U8x('bHdrReleaseModeExponential')

    elif cls.version <= 122:
        obj.U8x('byBitVector') \
           .bit('bMainOutputHierarchy', obj.lastval, 0) \
           .bit('bIsBackgroundMusic', obj.lastval, 1)

        obj.U8x('byBitVector') \
           .bit('bKillNewest', obj.lastval, 0) \
           .bit('bUseVirtualBehavior', obj.lastval, 1)

        obj.U16('u16MaxNumInstance')
        obj.U32('uChannelConfig') \
           .bit('uNumChannels', obj.lastval, 0, 0xFF) \
           .bit('eConfigType',  obj.lastval, 8, 0xF, fmt=wdefs.AkChannelConfigType) \
           .bit('uChannelMask', obj.lastval, 12, 0xFFFFF, fmt=wdefs.fmt_ch)

        obj.U8x('byBitVector') \
           .bit('bIsHdrBus', obj.lastval, 0) \
           .bit('bHdrReleaseModeExponential', obj.lastval, 1)

    else:
        obj.U8x('byBitVector') \
           .bit('bKillNewest', obj.lastval, 0) \
           .bit('bUseVirtualBehavior', obj.lastval, 1) \
           .bit('bIsMaxNumInstIgnoreParent', obj.lastval, 2) \
           .bit('bIsBackgroundMusic', obj.lastval, 3)

        obj.U16('u16MaxNumInstance')
        obj.U32('uChannelConfig') \
           .bit('uNumChannels', obj.lastval, 0, 0xFF) \
           .bit('eConfigType',  obj.lastval, 8, 0xF, fmt=wdefs.AkChannelConfigType) \
           .bit('uChannelMask', obj.lastval, 12, 0xFFFFF, fmt=wdefs.fmt_ch)

        obj.U8x('byBitVector') \
           .bit('bIsHdrBus', obj.lastval, 0) \
           .bit('bHdrReleaseModeExponential', obj.lastval, 1)

    return

#026>=
def CAkBus__SetInitialValues(obj, cls):
    #CAkBus::SetInitialValues
    obj = obj.node('BusInitialValues')

    obj.tid('OverrideBusId').fnv(wdefs.fnv_bus)
    if cls.version <= 126:
        pass
    else:
        if obj.lastval == 0:
            obj.tid('idDeviceShareset')

    cls.CAkClass__SetInitialParams(obj, cls) #_vptr$CAkIndexable + 17 (v135<=), _vptr$IAkEffectSlotsOwner + 17

    if cls.version <= 52:
        obj.tid('ulStateGroupID').fnv(wdefs.fnv_var)
    else:
        pass

    obj.s32('RecoveryTime')

    if cls.version <= 38:
        pass
    else:
        obj.f32('fMaxDuckVolume')

    if cls.version <= 52:
        obj.U32('eStateSyncType').fmt(wdefs.AkSyncType)
    else:
        pass


    obj.u32('ulDucks')
    for elem in obj.list('ToDuckList', 'AkDuckInfo', obj.lastval):
        elem.tid('BusID').fnv(wdefs.fnv_bus) #sometimes bank hashnames too
        elem.f32('DuckVolume')
        elem.s32('FadeOutTime')
        elem.s32('FadeInTime')
        elem.U8x('eFadeCurve').fmt(wdefs.AkCurveInterpolation)
        if cls.version <= 65: #65=DmC
            pass
        else:
            elem.U8x('TargetProp').fmt(wdefs.AkPropID)

    cls.CAkClass__SetInitialFxParams(obj, cls) #_vptr$CAkIndexable + 71 (v135<=), _vptr$IAkEffectSlotsOwner + 70

    if   cls.version <= 89:
        pass
    elif cls.version <= 145:
        obj.U8x('bOverrideAttachmentParams')
    else:
        pass

    if   cls.version <= 136:
        pass
    else:
        cls.CAkClass__SetInitialMetadataParams(obj, cls) #_vptr$IAkEffectSlotsOwner + 71

    SetInitialRTPC_CAkBus_(obj, cls)

    if   cls.version <= 52: #similar to ReadStateChunk but inline'd
        sub = obj.node('StateChunk') #not in original code but a bit hard to understand otherwise

        sub.u32('ulNumStates')
        for elem in sub.list('pStates', 'AKBKStateItem', sub.lastval):
            elem.tid('ulStateID').fnv(wdefs.fnv_val)
            elem.U8x('bIsCustom')
            elem.tid('ulStateInstanceID').fnv(wdefs.fnv_no)

    elif cls.version <= 122:
        CAkParameterNodeBase__ReadStateChunk(obj, cls)

    elif cls.version <= 126:
        CAkStateAware__ReadStateChunk(obj, cls)

    else:
        cls.CAkClass__ReadStateChunk(obj, cls) #callback but same


    if   cls.version <= 126:
        CAkParameterNodeBase__ReadFeedbackInfo(obj, cls)
    else:
        pass

    return

#-
def CAkBankMgr__ReadBus(obj):
    #CAkBankMgr::ReadBus
    cls = wcls.CAkBus__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_bus) #usually hashname

    CAkBus__SetInitialValues(obj, cls) #callback, can only logically be this
    return


#******************************************************************************
# HIRC: Layer Container

#046>=
def CAkLayer__SetInitialValues(obj, cls):
    #CAkLayer::SetInitialValues
    obj = obj.node('LayerInitialValues')

    SetInitialRTPC_CAkLayer_(obj, cls)

    obj.tid('rtpcID').fnv(wdefs.fnv_gmx) #depends on target (ex. modulator=guidname, curve=hashname)

    if cls.version <= 89:
        pass
    else:
        obj.U8x('rtpcType').fmt(wdefs.AkRtpcType)

    if cls.version <= 56:
        obj.f32('fCrossfadingRTPCDefaultValue')
    else:
        pass

    obj.u32('ulNumAssoc')
    for elem in obj.list('assocs', 'CAssociatedChildData', obj.lastval):
        elem.tid('ulAssociatedChildID').fnv(wdefs.fnv_no)
        if is_custom(obj):
            elem.U8x('unknown_custom') #0/1?
            elem.U8x('unknown_custom') #0/1?
        elem.u32('ulCurveSize')
        parse_rtpc_graph(elem) #set on 'assocs'

    return

#046>=
def CAkLayerCntr__SetInitialValues(obj, cls):
    #CAkLayerCntr::SetInitialValues
    obj = obj.node('LayerCntrInitialValues')

    CAkParameterNodeBase__SetNodeBaseParams(obj, cls)

    CAkParentNode_CAkParameterNode___SetChildren(obj, cls)

    obj.u32('ulNumLayers')
    for elem in obj.list('pLayers', 'CAkLayer', obj.lastval):
        elem.tid('ulLayerID').fnv(wdefs.fnv_no) #indirect read in 113

        CAkLayer__SetInitialValues(elem, cls)

    if cls.version <= 118:
        pass
    else:
        obj.U8x('bIsContinuousValidation')

    return

#-
def CAkBankMgr__StdBankRead_CAkLayerCntr_CAkParameterNodeBase_(obj):
    #CAkBankMgr::StdBankRead<CAkLayerCntr,CAkParameterNodeBase>
    #CAkBankMgr::StdBankRead<CAkLayerCntr>
    cls = wcls.CAkLayerCntr__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkLayerCntr__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Music Segment

#046>=
def CAkMusicNode__SetMusicNodeParams(obj, cls):
    #CAkMusicNode::SetMusicNodeParams
    obj = obj.node('MusicNodeParams')

    if cls.version <= 89:
        pass
    else:
        obj.U8x('uFlags') \
            .bit('bOverrideParentMidiTempo', obj.lastval, 1) \
            .bit('bOverrideParentMidiTarget', obj.lastval, 2) \
            .bit('bMidiTargetTypeBus', obj.lastval, 3)

    CAkParameterNodeBase__SetNodeBaseParams(obj, cls)

    CAkParentNode_CAkParameterNode___SetChildren(obj, cls)

    for elem in [obj.node('AkMeterInfo')]:
        elem.d64('fGridPeriod')
        elem.d64('fGridOffset')
        elem.f32('fTempo')
        elem.u8i('uTimeSigNumBeatsBar')
        elem.u8i('uTimeSigBeatValue')
    obj.U8x('bMeterInfoFlag') #override meter (0=off, !0=on)

    obj.u32('NumStingers')
    for elem in obj.list('pStingers', 'CAkStinger', obj.lastval):
        elem.tid('TriggerID').fnv(wdefs.fnv_trg)
        elem.tid('SegmentID').fnv(wdefs.fnv_no)
        elem.u32('SyncPlayAt').fmt(wdefs.AkSyncType)
        if cls.version <= 62:
            pass
        else: #65?
            elem.u32('uCueFilterHash')
        elem.s32('DontRepeatTime')
        elem.u32('numSegmentLookAhead')
    return

#046>=
def CAkMusicSegment__SetInitialValues(obj, cls):
    #CAkMusicSegment::SetInitialValues
    obj = obj.node('MusicSegmentInitialValues')

    CAkMusicNode__SetMusicNodeParams(obj, cls)

    obj.d64('fDuration')
    obj.u32('ulNumMarkers')
    for elem in obj.list('pArrayMarkers', 'AkMusicMarkerWwise', obj.lastval):
        if cls.version <= 62:
            elem.u32('id') #actually may be tid too but entry/exit use 0/1, other cues use ID (ex. Splatterhouse)
        else: #65=DmC
            elem.tid('id')
        elem.d64('fPosition')

        if   cls.version <= 62:
            pass
        elif cls.version <= 136:
            #AK::ReadBankStringUtf8
            elem.u32('uStringSize')
            if elem.lastval > 0:
                elem.str('pMarkerName', elem.lastval) #pszName
        else:
            #AK::ReadBankStringUtf8
            elem.stz('pMarkerName') #pszName

    if is_custom(obj) and cls.version <= 129:
        obj.u32('ulNumUnknown_custom')
        for elem in obj.list('p_unknown_custom', 'Unknown_custom', obj.lastval):
            elem.u32('unknown') #some ID, may repeat
            elem.u32('unknown') #sometimes 0?
            elem.u32('unknown') #always 0x40nnnnnn?
            elem.u32('unknown') #always 0?

    return

#-
def CAkBankMgr__StdBankRead_CAkMusicSegment_CAkParameterNodeBase_(obj):
    #CAkBankMgr::StdBankRead<CAkMusicSegment,CAkParameterNodeBase>
    #CAkBankMgr::StdBankRead<CAkMusicSegment>
    cls = wcls.CAkMusicSegment__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkMusicSegment__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Music Track

#112>=
def TrackSwitchInfo__SetTransParams(obj, cls):
    #TrackSwitchInfo::SetTransParams
    obj = obj.node('TransParams')

    for elem in [obj.node('srcFadeParams')]: #AkMusicFade
        elem.s32('transitionTime')
        elem.u32('eFadeCurve').fmt(wdefs.AkCurveInterpolation)
        elem.s32('iFadeOffset')
    obj.u32('eSyncType').fmt(wdefs.AkSyncType)
    obj.u32('uCueFilterHash')
    for elem in [obj.node('destFadeParams')]: #AkMusicFade
        elem.s32('transitionTime')
        elem.u32('eFadeCurve').fmt(wdefs.AkCurveInterpolation)
        elem.s32('iFadeOffset')
    return

#112>=
def TrackSwitchInfo__SetSwitchParams(obj, cls):
    #TrackSwitchInfo::SetSwitchParams
    obj = obj.node('SwitchParams')

    obj.U8x('eGroupType').fmt(wdefs.AkGroupType)
    obj.tid('uGroupID').fnv(wdefs.fnv_var)
    obj.tid('uDefaultSwitch').fnv(wdefs.fnv_val)
    obj.u32('numSwitchAssoc')
    for elem in obj.list('arSwitchAssoc', 'TrackSwitchAssoc', obj.lastval):
        elem.tid('ulSwitchAssoc').fnv(wdefs.fnv_val)
    return

#112>=
def CAkMusicTrack__SetTransParams(obj, cls):
    #CAkMusicTrack::SetTransParams
    TrackSwitchInfo__SetTransParams(obj, cls)
    return

#112>=
def CAkMusicTrack__SetSwitchParams(obj, cls):
    #CAkMusicTrack::SetSwitchParams
    TrackSwitchInfo__SetSwitchParams(obj, cls)
    return

#048>=
def CAkMusicTrack__SetInitialValues(obj, cls):
    #CAkMusicTrack::SetInitialValues
    obj = obj.node('MusicTrackInitialValues')

    if cls.version <= 89:
        pass
    elif cls.version <= 112:
        obj.U8x('uOverrides') \
           .bit('bOverrideParentMidiTempo', obj.lastval, 1) \
           .bit('bOverrideParentMidiTarget', obj.lastval, 2)
    elif cls.version <= 152:
        obj.U8x('uFlags') \
            .bit('bOverrideParentMidiTempo', obj.lastval, 1) \
            .bit('bOverrideParentMidiTarget', obj.lastval, 2) \
            .bit('bMidiTargetTypeBus', obj.lastval, 3)
    else:
        pass

    obj.u32('numSources')
    count = obj.lastval

    if cls.version <= 26:
        obj2 = obj.node('DataIndexes')
        for _i in range(0, count):
            obj2.u32('dataIndex') #low number

    for elem in obj.list('pSource', 'AkBankSourceData', count): #CAkMusicSource
        CAkBankMgr__LoadSource(elem, cls, True)

    if   cls.version <= 152:
        pass
    else:
        obj.U8x('uFlags') \
            .bit('bOverrideParentMidiTempo', obj.lastval, 1) \
            .bit('bOverrideParentMidiTarget', obj.lastval, 2) \
            .bit('bMidiTargetTypeBus', obj.lastval, 3)

    if cls.version <= 26:
        pass
    else:
        obj.u32('numPlaylistItem')
        if obj.lastval > 0:
            for elem in obj.list('pPlaylist', 'AkTrackSrcInfo', obj.lastval):
                elem.u32('trackID') #0..N
                elem.tid('sourceID').fnv(wdefs.fnv_no)
                if cls.version <= 150:
                    pass
                else:
                    elem.U32('cacheID') #part of a 128-bit hash, sometimes from in .wem's "hash" chunk
                if cls.version <= 132:
                    pass
                else:
                    elem.tid('eventID')
                elem.d64('fPlayAt')
                elem.d64('fBeginTrimOffset')
                elem.d64('fEndTrimOffset')
                elem.d64('fSrcDuration')
            obj.u32('numSubTrack')

    if cls.version <= 62:
        pass
    else: #65=DmC
        obj.u32('numClipAutomationItem')
        for elem in obj.list('pItems', 'AkClipAutomation', obj.lastval):
            elem.u32('uClipIndex')
            elem.U32('eAutoType').fmt(wdefs.AkClipAutomationType)
            elem.u32('uNumPoints')
            parse_rtpc_graph(elem, name='pArrayGraphPoints')

    CAkParameterNodeBase__SetNodeBaseParams(obj, cls)

    if cls.version <= 56:
        obj.s16('Loop')
        obj.s16('LoopMod.min')
        obj.s16('LoopMod.max')
    else:
        pass

    if cls.version <= 89:
        obj.u32('eRSType').fmt(wdefs.AkMusicTrackRanSeqType)
    else:
        obj.U8x('eTrackType').fmt(wdefs.AkMusicTrackType)
        if obj.lastval == 0x3:
            CAkMusicTrack__SetSwitchParams(obj, cls)
            CAkMusicTrack__SetTransParams(obj, cls)

    obj.s32('iLookAheadTime')

    if cls.version <= 26:
        obj.u32('numPlaylistItem')
        if obj.lastval > 0:
            for elem in obj.list('pPlaylist', 'AkTrackSrcInfo', obj.lastval):
                elem.u32('unknown') #0 even with N subtracks?
                elem.tid('sourceID').fnv(wdefs.fnv_no)
                elem.d64('fPlayAt')
                elem.d64('fBeginTrimOffset')
                elem.d64('fEndTrimOffset')
                elem.d64('fSrcDuration')
        obj.u32('unknown') #flag
    else:
        pass

    return

#-
def CAkBankMgr__ReadSourceParent_CAkMusicTrack_(obj):
    #CAkBankMgr::ReadSourceParent<CAkMusicTrack>
    cls = wcls.CAkMusicTrack__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkMusicTrack__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Music Switch

def parse_tree_node(obj, cls, count, count_max, cur_depth, max_depth, item_size):

    nodes = []
    for elem in obj.list('pNodes', 'Node', count):
        omax, offset = elem.offset_info()

        elem.tid('key').fnv(wdefs.fnv_val) #0/default or gamesync

        # Trees "should" reach max depth, but somehow v122 (and some v134) has dialogue trees
        # mixing depth 3 and 2 [battle_vo_orders__core.bnk's 50994472].
        # Technically could be possible by manually calling ResolveDialogueEvent with
        # 2 args instead of 3. Key doesn't seem to affect if tree ends (seen all combos
        # of 0/0/123, 0/123/0, 123/123/0, ... then 123/0), ::_ResolvePath doesn't look
        # like doing special detection, and only in a few leafs so may just be a bnk bug.

        # try to autodetect based on next value:
        id_ch = elem.peek32()
        uidx = (id_ch >> 0)  & 0xFFFF
        ucnt = (id_ch >> 16) & 0xFFFF
        is_id = uidx > count_max or ucnt > count_max  # reliable enough...
        is_over = omax and offset + ucnt * item_size > omax # for rare cases in (updated') battle_vo_orders__core.bnk

        is_max = cur_depth == max_depth

        if is_max or is_id or is_over:
            elem.tid('audioNodeId').fnv(wdefs.fnv_no)
            children_count = 0
        else:
            elem.u16('children.uIdx')
            elem.u16('children.uCount')
            children_count = elem.lastval

        if   cls.version <= 29: #29=AoT2 test banks
            pass
        elif cls.version <= 36: #36=UFC
            elem.u16('uWeight')
            elem.u16('uProbability')
        elif cls.version <= 45: #45=AoT2
            pass
        else:
            elem.u16('uWeight')
            elem.u16('uProbability')

        nodes.append((elem, children_count))

    for elem, children_count in nodes:
        if children_count > 0:
            parse_tree_node(elem, cls, children_count, count_max, cur_depth+1, max_depth, item_size)

    return

# linear parse for tests
def parse_tree_linear(obj, cls, count_max):
    for elem in obj.list('pNodes', 'Node', count_max):
        elem.tid('key')

        id_ch = elem.peek32()
        uidx = (id_ch >> 0)  & 0xFFFF
        ucnt = (id_ch >> 16) & 0xFFFF
        is_id = uidx > count_max or ucnt > count_max  # reliable enough...
        #is_none = elem.lastval != 0 #not correct but works most of the time

        if is_id:
            elem.tid('audioNodeId').fnv(wdefs.fnv_no)
        else:
            elem.u16('children.uIdx')
            elem.u16('children.uCount')

        if   cls.version <= 29: #29=AoT2 test banks
            pass
        elif cls.version <= 36: #36=UFC
            elem.u16('uWeight')
            elem.u16('uProbability')
        elif cls.version <= 45: #45=AoT2
            pass
        else:
            elem.u16('uWeight')
            elem.u16('uProbability')

#048>=
def AkDecisionTree__SetTree(obj, cls, size, depth):
    #AkDecisionTree::Init #053<=
    #AkDecisionTree::SetTree
    obj = obj.node('AkDecisionTree')
    obj.omax(size)

    # This tree is a linear array of AkDecisionTree::Node, used in
    # AkDecisionTree::ResolvePath rather than pre-parsed, and selects
    # an ID typically based on probability and weight + states.
    #
    # Format: node > all children from node > all children of first child,
    # repeat until max depth (nodes always have children up to max).
    # idx is where the children start in the array. example:
    #
    # node[0]            idx=1, chl=1, dp=0   (max depth=4)
    #   node[1]          idx=2, chl=2, dp=1   (parent: [0])
    #     node[2]        idx=4, chl=2, dp=2   (parent: [1])
    #     node[3]        idx=8, chl=1, dp=2   (parent: [1])
    #       node[4]      idx=6, chl=1, dp=3   (parent: [2])
    #       node[5]      idx=7, chl=1, dp=3   (parent: [2])
    #         node[6]    audio node,   dp=4   (parent: [4])
    #         node[7]    audio node,   dp=4   (parent: [5])
    #       node[8]      idx=9, chl=1, dp=3   (parent: [3])
    #         node[9]    audio node,   dp=4   (parent: [8])
    #
    # We parse it to represents the final tree rather than the array, but
    # indexes get moved around and children idx makes less sense
    # (it's possible to read linearly but harder to know when it's an audio node)

    # see parse tree node
    if   cls.version <= 29:  #29=AoT2 test banks
        item_size = 0x08
    elif cls.version <= 36: #36=UFC
        item_size = 0x0c
    elif cls.version <= 45: #45=AoT2
        item_size = 0x08
    else:
        item_size = 0x0c

    count_max = size // item_size

    children_count = 1
    parse_tree_node(obj, cls, children_count, count_max, 0, depth, item_size)
    #parse_tree_linear(obj, cls, count_max)

    obj.consume()
    return

#088>=
def CAkMusicSwitchCntr__SetArguments(obj, count, unused=False):
    #CAkMusicSwitchCntr::SetArguments
    obj = obj.node('Arguments')

    elems = obj.list('pArguments', 'AkGameSync', count).preload()
    for elem in elems: #pArguments list
        elem.tid('ulGroup').fnv(wdefs.fnv_var)
    for elem in elems: #pGroupTypes list
        elem.U8x('eGroupType').fmt(wdefs.AkGroupType)
    return

#046>=
def CAkMusicSwitchCntr__SetInitialValues(obj, cls):
    #CAkMusicSwitchCntr::SetInitialValues
    obj = obj.node('MusicSwitchCntrInitialValues')

    CAkMusicTransAware__SetMusicTransNodeParams(obj, cls)

    if cls.version <= 72:
        obj.U32('eGroupType').fmt(wdefs.AkGroupType)
        obj.tid('ulGroupID').fnv(wdefs.fnv_var)
        obj.tid('ulDefaultSwitch').fnv(wdefs.fnv_val)
        obj.U8x('bIsContinuousValidation') #!=0
        obj.u32('numSwitchAssocs')
        for elem in obj.list('pAssocs', 'AkMusicSwitchAssoc', obj.lastval):
            elem.tid('switchID').fnv(wdefs.fnv_val)
            elem.tid('nodeID').fnv(wdefs.fnv_no)

    else:
        obj.U8x('bIsContinuePlayback')
        obj.u32('uTreeDepth')
        depth = obj.lastval

        CAkMusicSwitchCntr__SetArguments(obj, depth)
        obj.U32('uTreeDataSize')
        size = obj.lastval

        obj.U8x('uMode').fmt(wdefs.AkDecisionTree__Mode)

        AkDecisionTree__SetTree(obj, cls, size, depth)

    return

#-
def CAkBankMgr__StdBankRead_CAkMusicSwitchCntr_CAkParameterNodeBase_(obj):
    #CAkBankMgr::StdBankRead<CAkMusicSwitchCntr,CAkParameterNodeBase>
    cls = wcls.CAkMusicSwitchCntr__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkMusicSwitchCntr__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Music Random Sequence

#046>=
def CAkMusicTransAware__SetMusicTransNodeParams(obj, cls):
    #CAkMusicTransAware::SetMusicTransNodeParams
    obj = obj.node('MusicTransNodeParams')

    CAkMusicNode__SetMusicNodeParams(obj, cls)

    obj.u32('numRules')
    for elem in obj.list('pRules', 'AkMusicTransitionRule', obj.lastval):

        if cls.version <= 72:
            numsrc = 1
        else:
            elem.u32('uNumSrc')
            numsrc = elem.lastval

        for _i in range(numsrc):
            elem.tid('srcID').fnv(wdefs.fnv_no) #-1 or sid

        if cls.version <= 72:
            numdst = 1
        else:
            elem.u32('uNumDst')
            numdst = elem.lastval

        for _i in range(numdst):
            elem.tid('dstID').fnv(wdefs.fnv_no)

        for elem2 in [elem.node('AkMusicTransSrcRule')]:
            elem2.s32('transitionTime')
            elem2.u32('eFadeCurve').fmt(wdefs.AkCurveInterpolation)
            elem2.s32('iFadeOffset')
            elem2.u32('eSyncType').fmt(wdefs.AkSyncType)
            if   cls.version <= 62:
                pass
            elif cls.version <= 72: #65=DmC
                elem2.u32('uMarkerID')
            else:
                elem2.u32('uCueFilterHash')
            elem2.U8x('bPlayPostExit')

        for elem2 in [elem.node('AkMusicTransDstRule')]:
            elem2.s32('transitionTime')
            elem2.u32('eFadeCurve').fmt(wdefs.AkCurveInterpolation)
            elem2.s32('iFadeOffset')
            if cls.version <= 72:
                elem2.u32('uMarkerID')
            else:
                elem2.u32('uCueFilterHash')
            elem2.tid('uJumpToID').fnv(wdefs.fnv_no)
            if cls.version <= 132:
                pass
            else:
                elem2.U16('eJumpToType').fmt(wdefs.AkJumpToSelType)
            elem2.U16('eEntryType').fmt(wdefs.AkEntryType)

            elem2.U8x('bPlayPreEntry')

            if cls.version <= 62:
                pass
            else: #65=DmC/ZoE
                elem2.U8x('bDestMatchSourceCueName')

        if is_custom(obj):
            elem.tid('ulStateGroupID?_custom').fnv(wdefs.fnv_var)
            elem.tid('ulStateID?_custom').fnv(wdefs.fnv_val)

        if cls.version <= 72:
            elem.U8x('bIsTransObjectEnabled')
            has_transobj = True #always! flag is used elsewhere
        else:
            elem.U8x('AllocTransObjectFlag')
            has_transobj = elem.lastval != 0

        if has_transobj:
            elem2 = elem.node('AkMusicTransitionObject')

            if cls.version <= 26: # no idea what's going on with all those
                elem2.u32('unknown')
            else:
                elem2.tid('segmentID').fnv(wdefs.fnv_no)

            if cls.version <= 26:
                #-1 only happens in SM:WoS PC (not X360 or other games), bug/uninitialized memory?
                for elem3 in [elem2.node('fadeInParams?')]: #AkMusicFade
                    elem3.s32('transitionTime?')
                    elem3.u32('eFadeCurve?')
                    elem3.s32('iFadeOffset?')

                for elem3 in [elem2.node('fadeOutParams?')]: #AkMusicFade
                    elem3.s32('transitionTime?')
                    elem3.u32('eFadeCurve?')
                    elem3.s32('iFadeOffset?')

            elif cls.version <= 34 and elem2.lastval == -1:
                #-1 only happens in SM:WoS PC (not X360 or other games), bug/uninitialized memory?
                for elem3 in [elem2.node('_fadeInParams')]: #AkMusicFade
                    elem3.s32('_transitionTime')
                    elem3.u32('_eFadeCurve')
                    elem3.s32('_iFadeOffset')

                for elem3 in [elem2.node('_fadeOutParams')]: #AkMusicFade
                    elem3.s32('_transitionTime')
                    elem3.u32('_eFadeCurve')
                    elem3.s32('_iFadeOffset')
            else:
                for elem3 in [elem2.node('fadeInParams')]: #AkMusicFade
                    elem3.s32('transitionTime')
                    elem3.u32('eFadeCurve').fmt(wdefs.AkCurveInterpolation)
                    elem3.s32('iFadeOffset')

                for elem3 in [elem2.node('fadeOutParams')]: #AkMusicFade
                    elem3.s32('transitionTime')
                    elem3.u32('eFadeCurve').fmt(wdefs.AkCurveInterpolation)
                    elem3.s32('iFadeOffset')

            if cls.version <= 26:
                elem2.U8x('bPlayPreEntry?')
                elem2.U8x('bPlayPostExit?')
            else:
                elem2.U8x('bPlayPreEntry')
                elem2.U8x('bPlayPostExit')
    return


def parse_playlist_node(obj, cls, count):

    for elem in obj.list('pPlayList', 'AkMusicRanSeqPlaylistItem', count):
        elem.tid('SegmentID').fnv(wdefs.fnv_no)
        elem.sid('playlistItemID').fnv(wdefs.fnv_no)
        elem.u32('NumChildren')
        children_count = elem.lastval

        if cls.version <= 36: #36=UFC, 35=JSpeed
            #this seems to work but not sure what are they going for, some fields may be wrong
            if elem.lastval != 0: #parent node
                elem.U32('eRSType').fmt(wdefs.RSType)
                elem.s16('Loop')
                elem.u16('Weight')
                if cls.version <= 35: #35=JSpeed
                    elem.u16('has_subnodes') #ok?
                    elem.U8x('bIsUsingWeight?')
                    elem.U8x('bIsShuffle?')
                else:
                    elem.u16('subnodes?') #ok?
                    elem.u16('subnodes?') #same?
                    elem.U8x('bIsUsingWeight?')
                    elem.U8x('bIsShuffle?')

            else: #child node
                elem.tid('nodeId?').fnv(wdefs.fnv_no) #same value for multiple children (varies with platform in SM:WOS)
                elem.s16('Loop')
                elem.u16('Weight')
                if cls.version <= 35: #35=JSpeed
                    elem.U16('unknown') #0001
                    elem.U8x('unknown') #00
                    elem.U8x('unknown') #00
                else:
                    elem.U16('unknown') #6785
                    elem.U16('unknown') #004C
                    elem.U8x('unknown') #00/01/05/0E/2D
                    elem.U8x('unknown') #00

        else:
            if cls.version <= 44: #Mass Effect 2
                if children_count == 0:
                    elem.tid('nodeId?').fnv(wdefs.fnv_no) #same value for multiple children
                else:
                    elem.u32('eRSType').fmt(wdefs.RSType)
            else: #046 (Enslaved)
                elem.u32('eRSType').fmt(wdefs.RSType)
            elem.s16('Loop')
            if cls.version <= 89:
                pass
            else:
                elem.s16('LoopMin')
                elem.s16('LoopMax')

            if cls.version <= 56:
                elem.u16('Weight')
            else:
                elem.u32('Weight')

            elem.u16('wAvoidRepeatCount')
            elem.U8x('bIsUsingWeight')
            elem.U8x('bIsShuffle')


        parse_playlist_node(elem, cls, children_count)

    return

#046>=
def CAkMusicRanSeqCntr__SetInitialValues(obj, cls):
    #CAkMusicRanSeqCntr::SetInitialValues
    obj = obj.node('MusicRanSeqCntrInitialValues')

    CAkMusicTransAware__SetMusicTransNodeParams(obj, cls)

    obj.u32('numPlaylistItems')
    parse_playlist_node(obj, cls, 1)

    #playlists work linearly (unlike decision trees):
    #node[0]            ch=3
    #  node[1]          ch=2    (parent: [0])
    #    node[2]        ch=1    (parent: [1])
    #      node[3]      ch=0    (parent: [2])
    #    node[4]        ch=0    (parent: [1])
    #  node[5]          ch=0    (parent: [0])
    #  node[6]          ch=1    (parent: [0])
    #    node[7]        ch=0    (parent: [7])

    return

#-
def CAkBankMgr__StdBankRead_CAkMusicRanSeqCntr_CAkParameterNodeBase_(obj):
    #CAkBankMgr::StdBankRead<CAkMusicRanSeqCntr,CAkParameterNodeBase>
    #CAkBankMgr::StdBankRead<CAkMusicRanSeqCntr>
    cls = wcls.CAkMusicRanSeqCntr__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkMusicRanSeqCntr__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Attenuation

#026>=
def CAkAttenuation__SetInitialValues(obj, cls):
    #CAkAttenuation::SetInitialValues
    obj = obj.node('AttenuationInitialValues')

    if   cls.version <= 136:
        pass
    else:
        obj.U8x('bIsHeightSpreadEnabled')

    obj.U8x('bIsConeEnabled')
    if (obj.lastval & 1):
        elem = obj.node('ConeParams')
        elem.f32('fInsideDegrees') #fInsideAngle = ToRadians(in_fDegrees) * 0.5
        elem.f32('fOutsideDegrees') #fOutsideAngle = ToRadians(in_fDegrees) * 0.5
        elem.f32('fOutsideVolume')
        elem.f32('LoPass')
        if cls.version <= 89:
            pass
        else:
            elem.f32('HiPass')

    if   cls.version <= 62:
        num_curves = 5
    #if   cls.version <= 65: #todo unknown
    #    num_curves = ?
    elif cls.version <= 72:
        num_curves = 4
    elif cls.version <= 89:
        num_curves = 5
    elif cls.version <= 141:
        num_curves = 7
    elif cls.version <= 154:
        num_curves = 19
    else:
        num_curves = 24

    for i in range(num_curves):
        obj.s8i('curveToUse[%i]' % i) #read as u8 but set to s8

    if cls.version <= 36: #36=UFC
        obj.U32('NumCurves')
    else:
        obj.U8x('NumCurves')

    for elem in obj.list('curves', 'CAkConversionTable', obj.lastval):
        if cls.version <= 36: #36=UFC
            elem.U32('eScaling').fmt(wdefs.AkCurveScaling)
            elem.u32('ulSize')
        else:
            elem.U8x('eScaling').fmt(wdefs.AkCurveScaling)
            elem.u16('ulSize')
        parse_rtpc_graph(elem)

    #inline'd in 113<=
    SetInitialRTPC_CAkAttenuation_(obj, cls)
    return

#-
def CAkBankMgr__StdBankRead_CAkAttenuation_CAkAttenuation_(obj):
    #CAkBankMgr::StdBankRead<CAkAttenuation,CAkAttenuation>
    #CAkBankMgr::StdBankRead<CAkAttenuation>
    cls = wcls.CAkAttenuation__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkAttenuation__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Dialogue Event

#026>=
def CAkDialogueEvent__SetInitialValues(obj, cls):
    #CAkDialogueEvent::SetInitialValues
    obj = obj.node('DialogueEventInitialValues')

    if cls.version <= 72:
        #argsize = 0x04
        pass
    else:
        #argsize = 0x05
        obj.u8i('uProbability')

    obj.u32('uTreeDepth')
    depth = obj.lastval

    # apparently skipped by Wwise, but wouldn't be able to tell arg types otherwise?
    #obj.gap('_pArguments', argsize * depth)
    subobj = obj.node('Arguments')
    if cls.version <= 72:
        elems = subobj.list('pArguments', 'AkGameSync', depth).preload()
        for elem in elems: #pArguments list
            elem.tid('ulGroup').fnv(wdefs.fnv_var)
        #eGroupType seems to default to "state"
    else:
        elems = subobj.list('pArguments', 'AkGameSync', depth).preload()
        for elem in elems: #pArguments list
            elem.tid('ulGroup').fnv(wdefs.fnv_var)
        for elem in elems: #pGroupTypes list
            elem.U8x('eGroupType').fmt(wdefs.AkGroupType)

    obj.U32('uTreeDataSize')
    size = obj.lastval

    if   cls.version <= 45: #45=AoT2
        pass
    elif cls.version <= 72:
        obj.u8i('uProbability')
    else:
        pass

    if cls.version <= 45: #45=AoT2
        pass
    else:
        obj.U8x('uMode').fmt(wdefs.AkDecisionTree__Mode)

    AkDecisionTree__SetTree(obj, cls, size, depth)

    if   cls.version <= 118:
        pass
    else:
        AkPropBundle_AkPropValue_unsigned_char___SetInitialParams(obj, cls)

        AkPropBundle_RANGED_MODIFIERS_AkPropValue__unsigned_char___SetInitialParams(obj, cls)

    return

#-
def CAkBankMgr__StdBankRead_CAkDialogueEvent_CAkDialogueEvent_(obj):
    #CAkBankMgr::StdBankRead<CAkDialogueEvent,CAkDialogueEvent>
    #CAkBankMgr::StdBankRead<CAkDialogueEvent>
    cls = wcls.CAkDialogueEvent__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_evt)

    CAkDialogueEvent__SetInitialValues(obj, cls)
    return

#******************************************************************************
# HIRC: Feedback Bus

#-
def CAkBankMgr__StdBankRead_CAkFeedbackBus_CAkParameterNodeBase_(obj):
    #CAkBankMgr::StdBankRead<CAkFeedbackBus,CAkParameterNodeBase>
    cls = wcls.CAkFeedbackBus__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_bus) #assumed

    #callback, can only logically be this
    CAkBus__SetInitialValues(obj, cls)
    return

#******************************************************************************
# HIRC: Feedback Node

#046>= 125<=
def CAkFeedbackNode__SetInitialValues(obj, cls):
    #CAkFeedbackNode::SetInitialValues
    obj = obj.node('FeedbackInitialValues')

    obj.u32('numSources')
    for elem in obj.list('pSource', 'AkBankSourceData', obj.lastval):
        elem.U16('CompanyID')
        elem.U16('DeviceID')
        elem.f32('fVolumeOffset')
        CAkBankMgr__LoadSource(elem, cls, True)

    CAkParameterNodeBase__SetNodeBaseParams(obj, cls)

    if cls.version <= 56:
        obj.s16('Loop')
        obj.s16('LoopMod.min')
        obj.s16('LoopMod.max')
    else:
        pass

    return

def CAkBankMgr__ReadSourceParent_CAkFeedbackNode_(obj):
    #CAkBankMgr::ReadSourceParent<CAkFeedbackNode>
    cls = wcls.CAkFeedbackNode__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no) #assumed, behaves like an audio object

    CAkFeedbackNode__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Fx Share Set

#052>=
def CAkFxBase__SetInitialValues(obj, cls):
    #CAkFxBase::SetInitialValues
    obj = obj.node('FxBaseInitialValues')

    parse_plugin(obj, name='fxID') #obj.U32('fxID')
    plugin_id = obj.lastval

    wplg.parse_plugin_params(obj, plugin_id, 'uSize', 'pParamBlock')
    #obj.U32('uSize')
    #obj.gap('pParamBlock', obj.lastval)

    obj.u8i('uNumBankData')
    for elem in obj.list('media', 'AkMediaMap', obj.lastval):
        elem.u8i('index')
        elem.tid('sourceId').fnv(wdefs.fnv_no)

    #inline'd in 113<=
    SetInitialRTPC_CAkFxBase_(obj, cls)

    if cls.version <= 89:
        pass
    elif cls.version <= 126:
        if cls.version <= 122:
            pass
        else:
            obj.U8x('_unused')
            obj.U8x('_unused')

        obj.u16('ulNumInit')
        for elem in obj.list('rtpcinit', 'RTPCInit', obj.lastval):
            if cls.version <= 113:
                elem.U8x('ParamID').fmt(wdefs.AkRTPC_ParameterID)
            else:
                elem.var('ParamID').fmt(wdefs.AkRTPC_ParameterID)
            elem.f32('fInitValue')
    else:
        cls.CAkClass__ReadStateChunk(obj, cls)

        obj.u16('numValues')
        for elem in obj.list('propertyValues', 'PluginPropertyValue', obj.lastval):
            elem.var('propertyId').fmt(wdefs.AkRTPC_ParameterID)
            elem.U8x('rtpcAccum').fmt(wdefs.AkRtpcAccum)
            elem.f32('fValue')

    return

#-
def CAkBankMgr__StdBankRead_CAkFxShareSet_CAkFxShareSet_(obj):
    #CAkBankMgr::StdBankRead<CAkFxShareSet,CAkFxShareSet>
    #CAkBankMgr::StdBankRead<CAkFxShareSet>
    cls = wcls.CAkFxShareSet__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_sfx)

    CAkFxBase__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Fx Custom

#-
def CAkBankMgr__StdBankRead_CAkFxCustom_CAkFxCustom_(obj):
    #CAkBankMgr::StdBankRead<CAkFxCustom,CAkFxCustom>
    #CAkBankMgr::StdBankRead<CAkFxCustom>
    cls = wcls.CAkFxCustom__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID') #.fnv(wdefs.fnv_sfx) #seemingly not fnv

    CAkFxBase__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Auxiliary Bus

#-
def CAkBankMgr__StdBankRead_CAkAuxBus_CAkParameterNodeBase_(obj):
    #CAkBankMgr::ReadAuxBus 120<=
    #CAkBankMgr::StdBankRead<CAkAuxBus,CAkParameterNodeBase> 125>=
    #CAkBankMgr::StdBankRead<CAkAuxBus>
    cls = wcls.CAkAuxBus__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_bus) #usually hashname

    CAkBus__SetInitialValues(obj, cls) #callback, can only logically be this
    return


#******************************************************************************
# HIRC: LFO

#112>=
def CAkModulator__SetInitialValues(obj, cls):
    #CAkModulator::SetInitialValues
    obj = obj.node('ModulatorInitialValues')

    AkPropBundle_AkPropValue_unsigned_char___SetInitialParams(obj, cls, modulator=True)

    AkPropBundle_RANGED_MODIFIERS_AkPropValue__unsigned_char___SetInitialParams(obj, cls, modulator=True)

    SetInitialRTPC_CAkModulator_(obj, cls) #inline'd in 113
    return

#- (112>=)
def CAkBankMgr__StdBankRead_CAkLFOModulator_CAkModulator_(obj):
    #CAkBankMgr::StdBankRead<CAkLFOModulator,CAkModulator>
    #CAkBankMgr::StdBankRead<CAkLFOModulator>
    cls = wcls.CAkLFOModulator__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkModulator__SetInitialValues(obj, cls) # callback in older versions
    return


#******************************************************************************
# HIRC: Envelope

#- (112>=)
def CAkBankMgr__StdBankRead_CAkEnvelopeModulator_CAkModulator_(obj):
    #CAkBankMgr::StdBankRead<CAkEnvelopeModulator,CAkModulator>
    #CAkBankMgr::StdBankRead<CAkEnvelopeModulator>
    cls = wcls.CAkEnvelopeModulator__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    #callback, can only logically be this
    CAkModulator__SetInitialValues(obj, cls) #_vptr$CAkIndexable + ?
    return


#******************************************************************************
# HIRC: Audio Device

#- (140>=)
def CAkAudioDevice__SetInitialValues(obj, cls):
    #CAkAudioDevice::SetInitialValues
    obj = obj.node('AudioDeviceInitialValues')

    CAkFxBase__SetInitialValues(obj, cls)
    CAkEffectSlots__SetInitialValues(obj, cls)
    return

#- (118>=)
def CAkBankMgr__StdBankRead_CAkAudioDevice_CAkAudioDevice_(obj):
    #CAkBankMgr::StdBankRead<CAkAudioDevice,CAkAudioDevice>
    #CAkBankMgr::StdBankRead<CAkAudioDevice>
    cls = wcls.CAkAudioDevice__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_sfx)

    if    cls.version <= 136:
        CAkFxBase__SetInitialValues(obj, cls)
    else:
        CAkAudioDevice__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC: Time Mod

#- (128>)
def CAkBankMgr__StdBankRead_CAkTimeModulator_CAkModulator_(obj):
    #CAkBankMgr::StdBankRead<CAkTimeModulator,CAkModulator>
    #CAkBankMgr::StdBankRead<CAkTimeModulator>
    cls = wcls.CAkTimeModulator__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    #callback, can only logically be this
    CAkModulator__SetInitialValues(obj, cls) #_vptr$CAkIndexable + ?
    return


#******************************************************************************
# HIRC: Sidechain

#168>=
def CAkSidechainMixIndexable__SetInitialValues(obj, cls):
    #CAkSidechainMixIndexable::SetInitialValues
    obj = obj.node('SidechainMixInitialValues')

    obj.tid('uId') #.fnv(wdefs.fnv_?)

    obj.U32('channelCfg').fmt(wdefs.AkChannelConfigType)

    return

#- (168>=)
def CAkBankMgr__ReadSidechainMix(obj):
    #CAkBankMgr::ReadSidechainMix
    cls = wcls.CAkSidechainMixIndexable__Create(obj)
    obj.set_name(cls.name)

    obj.sid('ulID').fnv(wdefs.fnv_no)

    CAkSidechainMixIndexable__SetInitialValues(obj, cls)
    return


#******************************************************************************
# HIRC

def CAkBankReader__Skip(obj):
    obj.gap('unused', obj.lastval)
    return

def parse_hirc_default(obj):
    #obj.gap('ignored', obj.lastval)
    return

#046>=
def get_hirc_dispatch(obj):
    hirc_dispatch = {
        0x01: CAkBankMgr__ReadState,
        0x02: CAkBankMgr__ReadSourceParent_CAkSound_,
        0x03: CAkBankMgr__ReadAction,
        0x04: CAkBankMgr__ReadEvent,
        0x05: CAkBankMgr__StdBankRead_CAkRanSeqCntr_CAkParameterNodeBase_,
        0x06: CAkBankMgr__StdBankRead_CAkSwitchCntr_CAkParameterNodeBase_,
        0x07: CAkBankMgr__StdBankRead_CAkActorMixer_CAkParameterNodeBase_,
        0x08: CAkBankMgr__ReadBus,
        0x09: CAkBankMgr__StdBankRead_CAkLayerCntr_CAkParameterNodeBase_,
        0x0a: CAkBankMgr__StdBankRead_CAkMusicSegment_CAkParameterNodeBase_,
        0x0b: CAkBankMgr__ReadSourceParent_CAkMusicTrack_,
        0x0c: CAkBankMgr__StdBankRead_CAkMusicSwitchCntr_CAkParameterNodeBase_,
        0x0d: CAkBankMgr__StdBankRead_CAkMusicRanSeqCntr_CAkParameterNodeBase_,
        0x0e: CAkBankMgr__StdBankRead_CAkAttenuation_CAkAttenuation_,
        0x0f: CAkBankMgr__StdBankRead_CAkDialogueEvent_CAkDialogueEvent_,
    }

    version = get_version(obj)
    if   version <= 72:
        hirc_dispatch.update({
            0x10: CAkBankMgr__StdBankRead_CAkFeedbackBus_CAkParameterNodeBase_, #026~~
            0x11: CAkBankMgr__ReadSourceParent_CAkFeedbackNode_, #046>=
            0x12: CAkBankMgr__StdBankRead_CAkFxShareSet_CAkFxShareSet_, #052>=
            0x13: CAkBankMgr__StdBankRead_CAkFxCustom_CAkFxCustom_, #052>=
            0x14: CAkBankMgr__StdBankRead_CAkAuxBus_CAkParameterNodeBase_, #072>= (06x>=?)
        })
    elif version <= 126:
        hirc_dispatch.update({
            #0x10/11 in theory use CAkBankReader__Skip in SDK, but can be found in test banks
            0x10: CAkBankMgr__StdBankRead_CAkFeedbackBus_CAkParameterNodeBase_,
            0x11: CAkBankMgr__ReadSourceParent_CAkFeedbackNode_,
            0x12: CAkBankMgr__StdBankRead_CAkFxShareSet_CAkFxShareSet_,
            0x13: CAkBankMgr__StdBankRead_CAkFxCustom_CAkFxCustom_,
            0x14: CAkBankMgr__StdBankRead_CAkAuxBus_CAkParameterNodeBase_,
            0x15: CAkBankMgr__StdBankRead_CAkLFOModulator_CAkModulator_, #112>=
            0x16: CAkBankMgr__StdBankRead_CAkEnvelopeModulator_CAkModulator_, #112>=
            0x17: CAkBankMgr__StdBankRead_CAkAudioDevice_CAkAudioDevice_, #118>=
        })
    else:
        hirc_dispatch.update({
            0x10: CAkBankMgr__StdBankRead_CAkFxShareSet_CAkFxShareSet_,
            0x11: CAkBankMgr__StdBankRead_CAkFxCustom_CAkFxCustom_,
            0x12: CAkBankMgr__StdBankRead_CAkAuxBus_CAkParameterNodeBase_,
            0x13: CAkBankMgr__StdBankRead_CAkLFOModulator_CAkModulator_,
            0x14: CAkBankMgr__StdBankRead_CAkEnvelopeModulator_CAkModulator_,
            0x15: CAkBankMgr__StdBankRead_CAkAudioDevice_CAkAudioDevice_,
            0x16: CAkBankMgr__StdBankRead_CAkTimeModulator_CAkModulator_, #132>=
            0x17: CAkBankMgr__ReadSidechainMix, #168>=
        })

    return hirc_dispatch

#026>=
def CAkBankMgr__ProcessHircChunk(obj):
    #CAkBankMgr::ProcessHircChunk
    obj.set_name('HircChunk')

    version  = get_version(obj)

    hirc_dispatch = get_hirc_dispatch(obj)

    count = 0
    try:
        obj.u32('NumReleasableHircItem')
        for elem in obj.list('listLoadedItem', 'AkListLoadedItem', obj.lastval):

            #AkBank::AKBKSubHircSection
            if version <= 48:
                elem.U32('eHircType').fmt(wdefs.AkBank__AKBKHircType)
            else:
                elem.U8x('eHircType').fmt(wdefs.AkBank__AKBKHircType)
            hirc_type = elem.lastval
            elem.U32('dwSectionSize').omax()

            #Section.eHircType switch
            try:
                dispatch = hirc_dispatch.get(hirc_type, parse_hirc_default)
                dispatch(elem)
            except wmodel.ParseError as e:
                elem.add_error(str(e))

            elem.consume()
            count += 1

    except wio.ReaderError as e:
        raise wio.ReaderError('failed parsing HIRC item %s' %  (count)) #from e ##chain

    return


#******************************************************************************
# BKHD

#026>=
def CAkBankMgr__ProcessBankHeader(obj):
    #CAkBankMgr::ProcessBankHeader
    obj.set_name('BankHeader')
    version = get_version(obj)
    chunk_size = obj.lastval

    root = obj.get_root()

    obj = obj.node('AkBankHeader')

    if version <= 26:
        obj.U32('bInitializationBank') #flag 0/1
        obj.U32('unknown') #0/1
        obj.u32('dwBankGeneratorVersion')
        # no actual id so use timestamp below
        #root.set_id(root.get_bankname())

        is_be = root.is_be() #fix for Too Human not having feedback
        root.set_feedback(not is_be)

    else:
        if is_custom(obj):
            obj.U32('dwBankGeneratorVersion')
        else:
            obj.u32('dwBankGeneratorVersion')
        obj.sid('dwSoundBankID').fnv(wdefs.fnv_bnk)
        # needed to make txtp with mixed banks
        root.set_id(obj.lastval)

    if version <= 122:
        obj.u32('dwLanguageID').fmt(wdefs.language_id)
    else:
        obj.sid('dwLanguageID').fnv(wdefs.fnv_lng) #hashed lang string
    root.set_lang(obj.lastval)

    if version <= 26:
        obj.u64('timestamp?')
        root.set_id(obj.lastval)
    elif version <= 126:
        obj.U32('bFeedbackInBank') #bFeedbackSupported
        #in later versions seems 16b=feedback + 16b=?, but this is how it's read/checked
        root.set_feedback(obj.lastval & 1) #not (obj.lastval ^ 1)
    elif version <= 134:
        obj.U32('uAltValues') \
            .bit('bUnused', obj.lastval, 0, 0xFFFF) \
            .bit('bDeviceAllocated', obj.lastval, 16, 0xFFFF)
    else:
        obj.U32('uAltValues') \
            .bit('uAlignment', obj.lastval, 0, 0xFFFF) \
            .bit('bDeviceAllocated', obj.lastval, 16, 0xFFFF)

    if   version <= 76:
        project_id = 0
    else:
        obj.u32('dwProjectID')
        project_id = obj.lastval

    if version <= 141:
        pass
    else:
        obj.u32('dwSoundBankType').fmt(wdefs.AkBankTypeEnum)
        obj.gap('abyBankHash', 0x10) # u8[16] array

    # rest is skipped (not defined/padded), may be used for DATA alignment to sector size
    if   version <= 26:
        gap_size = chunk_size - 0x18 #there are always 0x08 after but not read by original code
    elif version <= 76:
        gap_size = chunk_size - 0x10
    elif version <= 141:
        gap_size = chunk_size - 0x14
    else:
        gap_size = chunk_size - 0x14 - 0x04 - 0x10
    if gap_size > 0:
        obj.gap('padding', gap_size)


    # * special detection for buggy banks
    
    # Star Fox Zero/Guard (v112) have some odd behavior in the feedback flag. All .bnk except init.bnk set it, but
    # no .bnk has feedback info. Presumably only init.bnk (first) flag's matters, but since we can't be sure
    # that bank was loaded, we need some crude autodetection.
    # Some test/remnant .bnk in SFZ use v88 and don't have the flag set, and no other 112 bnk exhibits this bug
    # either (flag works as intended), so maybe it happened in some Wwise revision only.
    if version == 112:
        is_be = root.is_be()
        if project_id in wdefs.v112_buggy_project_ids and is_be: #id not unique but seems unique enough for this case
            root.set_feedback(0)

    # Army of Two: the 40th Day banks range from v034~045, though init.bnk and most files use 045.
    # Most versions work ok, but *some* banks using v044 have one extra field in CAkRanseq like 045.
    # (no apparent flag, even banks almost 100% exactly like others, ex. VO_INT_CHI_GUARD or
    # gun_type_m249saw.bnk v44 vs gun_type_m249.bnk v45).
    # No other game with v044 does this (ME2, AC2, DLPOut), and in theory Wwise only loads one
    # version, so maybe init.bnk version is what matters or buggy banks/objects are rejected.
    # We'll autodetect to treat as v045 and read the extra field to avoid throwing errors.
    if version == 44:
        is_be = root.is_be() #seen in X360 and PS3 (though the later has a few less bnk)
        # since checks are a bit limited we need exact bank ids (Global_VO may be problematic though?)
        if project_id == 0 and not root.has_feedback() and is_be and root.get_id() in wdefs.aot2_buggy_banks:
            root.set_subversion(45)
            pass

    # how fun, Dance on Broadway (Wii) v45 has one less field than AoT2 v45, try to autodetect AoT2
    if version == 45:
        if not root.has_feedback(): #DoB all .bnk use feedback
            root.set_subversion(45)

    return


#******************************************************************************
# DATA

def parse_data_old(objp, chunk_size):

    # mix of index + data

    obj = objp.node('MediaIndex')
    obj.u32('uNumMedias')
    count = obj.lastval
    obj.U32('unknown') # null / optional header size?
    obj.U32('uMediasSize')
    obj.U32('uPaddingSize') # after entries before data
    padding = obj.lastval

    obj.U32('uChunkSize')
    obj.U32('unknown')
    obj.U32('uDataOffset')
    obj.U32('uDataSize')

    chunk_size -= 0x20

    for elem in obj.list('pLoadedMedia', 'MediaHeader', count):
        elem.u32('unknown') #always -1
        elem.U32('unknown') #always 0
        elem.u32('trackID?') #number (usually entry number) or -1
        elem.U32('unknown') #5 or -1?
        elem.U32('uOffset') #stream offset (from DATA) or -1 if none
        elem.U32('uSize') #stream size or 0 if none

        chunk_size -= 0x18

    obj.gap('pPadding', padding)

    chunk_size -= padding

    obj = objp.node('Data')
    obj.gap('pData', chunk_size)


#026>=
def CAkBankMgr__ProcessDataChunk(obj):
    #CAkBankMgr::ProcessDataChunk
    obj.set_name('DataChunk')
    chunk_size = obj.lastval
    version = get_version(obj)


    if version <= 26:
        parse_data_old(obj, chunk_size)
    else:
        obj.gap('pData', chunk_size)

    return


#******************************************************************************
# FXPR

#026>= 048<=
def CAkBankMgr__ProcessFxParamsChunk(obj):
    #CAkBankMgr::ProcessFxParamsChunk
    obj.set_name('FxParamsChunk')
    version = get_version(obj)

    obj.u32('ulNumParamSets')
    for elem in obj.list('pParams', 'FXParameterSet', obj.lastval):
        elem.tid('EnvID')
        parse_plugin(elem, 'FXID')
        plugin_id = elem.lastval
        wplg.parse_plugin_params(elem, plugin_id, 'ulPresetSize', 'pDataBlock')
        #elem.U32('ulPresetSize')
        #elem.gap('pDataBlock', elem.lastval)

        if version <= 46:
            pass
        else:
            elem.u32('ulNumBankData')
            for elem2 in elem.list('pParams', 'Plugin', elem.lastval):
                elem2.tid('FXParameterSetID') #plugin? (not seen)
                elem2.U32('item')

        if version <= 34: #34=LOTR, #34=SM
            elem.u32('ulRTPCSize')
        else:
            elem.u16('ulRTPCSize')

        for elem2 in elem.list('pRTPCMgr', 'RTPC', elem.lastval):
            if version <= 34: #34=LOTR
                parse_plugin(elem2, 'FXID')
            else:
                elem2.U32('pBufferToFill')
                elem2.u8i('uFXIndex')
            elem2.tid('RTPCID').fnv(wdefs.fnv_gmx) #depends on target (ex. modulator=guidname, curve=hashname)
            elem2.U32('ParamID').fmt(wdefs.AkRTPC_ParameterID)
            elem2.sid('rtpcCurveID') #fnv?
            if version <= 34: #34=LOTR (probably for 36 too since other parts need it
                elem2.u32('eScaling').fmt(wdefs.AkCurveScaling)
                elem2.u32('ulSize')
            else:
                elem2.U8x('eScaling').fmt(wdefs.AkCurveScaling)
                elem2.u16('ulSize')
            parse_rtpc_graph(elem2)

    return


#******************************************************************************
# STID

def parse_stid_old_entries(obj, type, size):
    obj.u32('entries')
    count = obj.lastval

    elem = obj.node('Offsets')
    for _i in range(0, count):
        elem.U32('offset') #points after all offsets, can be -1 (but name still exists)

    gap_size = size - 0x04 - count * 0x04
    obj.gap('strings', gap_size)
    
    # TODO when offset is -1 2nd hash doesn't become -1?
    # for _i in range(0, count):
    #     while True:
    #         obj.u32('hash')
    #         if obj.lastval == -1:
    #             break
    #         obj.stz('name')

def parse_stid_old_sub(obj, chunk_size):
    elem = obj.node('StringChunk')
    elem.U32('uiType') #.fmt(wdefs.AKBKStringType)
    type = elem.lastval
    chunk_size -= 0x04

    for elem2 in elem.list('pSub', 'StringSubchunk', type):
        elem2.tid('ulStateGroupID')
        elem2.U32('uiSize') #.omax()
        size = elem2.lastval
        parse_stid_old_entries(elem2, type, size)
        chunk_size -= (size + 0x08)

    return chunk_size

def parse_stid_old_base(obj, chunk_size):
    elem = obj.node('StringChunk')
    elem.U32('uiType') #.fmt(wdefs.AKBKStringType)
    type = elem.lastval
    chunk_size -= 0x04

    elem.U32('uiSize') #.omax()
    size = elem.lastval
    parse_stid_old_entries(elem, type, size)
    chunk_size -= (size + 0x04)

    if type in [2, 5, 9]:
        # sublist
        chunk_size = parse_stid_old_sub(elem, chunk_size)

    return chunk_size

def parse_stid_old(obj):
    #todo this looks like a tree but not sure of format
    chunk_size = obj.lastval

    while chunk_size:
        chunk_size = parse_stid_old_base(obj, chunk_size)
        continue
        elem = obj.node('StringChunk')
        elem.U32('uiType') #.fmt(wdefs.AKBKStringType)
        type = elem.lastval
        chunk_size -= 0x04

        # "type" seems to refer where it's used. Most bnk use 1=single (KK2 code defines 1/2/4/5/7/8/9/11)
        # but Init.bnk has 4/2/3/5/7 (some kind of tree?). 
        # 
        # Some types When starting type=4, 4/6th entry (including first)
        # has an slightly different format of sub-entries (seen for 3 and 7). Or maybe if prev type is 2 next has
        # sub-entries. Not sure about exact formula (few samples and code doesn't help) so use some crude autodetection.
        #test = elem.peek32() #crude autodetection if the formula below doesn't help
        #if test < 0x10000: #small size, seen ~0x1000
        
        #if test < 0x10000: #small size, seen ~0x1000
        elem.U32('uiSize') #.omax()
        size = elem.lastval
        parse_stid_old_entries(elem, type, size)
        chunk_size -= (size + 0x04)

        if type in [2, 7, 9]:
            elem2 = elem.node('StringChunk')
            elem2.U32('uiType') #.fmt(wdefs.AKBKStringType)

            for elem2 in elem.list('pSub', 'StringSubchunk', type):
                elem2.u32('unknown') #sid?
                elem2.U32('uiSize') #.omax()
                size = elem2.lastval
                parse_stid_old_entries(elem2, type, size)
                chunk_size -= (size + 0x08)


#046>=
def CAkBankMgr__ProcessStringMappingChunk(obj):
    #CAkBankMgr::ProcessStringMappingChunk
    obj.set_name('StringMappingChunk')
    version = get_version(obj)

    if version <= 26:
        parse_stid_old(obj)
        return

    obj.U32('uiType').fmt(wdefs.AKBKStringType)
    obj.U32('uiSize')
    for elem in obj.list('BankIDToFileName', 'AKBKHashHeader', obj.lastval):
        elem.tid('bankID').fnv(wdefs.fnv_bnk)
        elem.u8i('stringsize')
        elem.str('FileName', elem.lastval)
        if elem.lastval:
            elem.get_root().add_string(elem.lastval)
    return


#******************************************************************************
# STMG

#014>=
def CAkBankMgr__ProcessGlobalSettingsChunk(obj):
    #CAkBankMgr::ProcessGlobalSettingsChunk
    obj.set_name('GlobalSettingsChunk')
    version = get_version(obj)

    if version <= 140:
        pass
    else:
        obj.U16('uFilterBehavior').fmt(wdefs.AkFilterBehavior)

    obj.f32('fVolumeThreshold')

    if version <= 53:
        pass
    else:
        obj.u16('maxNumVoicesLimitInternal') #aka u16MaxVoices

    if version <= 126:
        pass
    else:
        obj.u16('maxNumDangerousVirtVoicesLimitInternal') #aka u16MaxVirtVoices

    if version <= 154:
        pass
    else:
        obj.f32('fHSFEmphasis')

    obj.u32('ulNumStateGroups')
    for elem in obj.list('StateGroups', 'AkStateGroup', obj.lastval):
        elem.sid('ulStateGroupID').fnv(wdefs.fnv_var)
        elem.u32('DefaultTransitionTime')

        if version <= 52:
            elem.u32('ulNumCustomStates')
            for elem2 in elem.list('mapTransitions', 'AkStateTransition', elem.lastval):
                elem2.tid('ulStateType') #ulStateID

                if version <= 48:
                    elem2.u32('eHircType').fmt(wdefs.AkBank__AKBKHircType)
                else:
                    elem2.U8x('eHircType').fmt(wdefs.AkBank__AKBKHircType)
                elem2.u32('dwSectionSize')

                obj_state = elem2.node('state')
                CAkBankMgr__ReadState(obj_state)
        else:
            pass

        elem.u32('ulNumTransitions')
        for elem2 in elem.list('mapTransitions', 'AkStateTransition', elem.lastval):
            elem2.tid('StateFrom').fnv(wdefs.fnv_val)
            elem2.tid('StateTo').fnv(wdefs.fnv_val)
            elem2.u32('TransitionTime')

    obj.u32('ulNumSwitchGroups')
    for elem in obj.list('pItems', 'SwitchGroups', obj.lastval):
        elem.tid('SwitchGroupID').fnv(wdefs.fnv_var)
        elem.tid('rtpcID').fnv(wdefs.fnv_gmx) #depends on target (ex. gamevar=hashname, rtpc=hashname, modulator=guidname)
        if version <= 89:
            pass
        else:
            elem.U8x('rtpcType').fmt(wdefs.AkRtpcType)
        elem.u32('ulSize')
        parse_rtpc_graph(elem, name='pSwitchMgr', subname='AkSwitchGraphPoint')

    if version <= 38:
        return
    else:
        pass

    obj.u32('ulNumParams')
    for elem in obj.list('pRTPCMgr', 'RTPCRamping', obj.lastval):
        elem.sid('RTPC_ID').fnv(wdefs.fnv_gme) #should be sid/base definition of gamevar/shareset RTPC (not modulator/etc that use guidnames)
        elem.f32('fValue')

        if version <= 89:
            pass
        else:
            elem.u32('rampType').fmt(wdefs.AkTransitionRampingType)
            elem.f32('fRampUp')
            elem.f32('fRampDown')
            elem.u8i('eBindToBuiltInParam').fmt(wdefs.AkBuiltInParam)

    if   version <= 118:
        pass
    elif version <= 122:
        obj.u32('ulNumTextures')
        for elem in obj.list('acousticTextures', 'AkAcousticTexture', obj.lastval):
            elem.sid('ID').fnv(wdefs.fnv_aco)
            elem.u16('OnOffBand1')
            elem.u16('OnOffBand2')
            elem.u16('OnOffBand3')
            elem.u16('FilterTypeBand1')
            elem.u16('FilterTypeBand2')
            elem.u16('FilterTypeBand3')
            elem.f32('FrequencyBand1')
            elem.f32('FrequencyBand2')
            elem.f32('FrequencyBand3')
            elem.f32('QFactorBand1')
            elem.f32('QFactorBand2')
            elem.f32('QFactorBand3')
            elem.f32('GainBand1')
            elem.f32('GainBand2')
            elem.f32('GainBand3')
            elem.f32('OutputGain')
    else:
        obj.u32('ulNumTextures')
        for elem in obj.list('acousticTextures', 'AkAcousticTexture', obj.lastval):
            elem.sid('ID').fnv(wdefs.fnv_aco)
            elem.f32('fAbsorptionOffset')
            elem.f32('fAbsorptionLow')
            elem.f32('fAbsorptionMidLow')
            elem.f32('fAbsorptionMidHigh')
            elem.f32('fAbsorptionHigh')
            elem.f32('fScattering')

    if   version <= 118:
        pass
    elif version <= 122:
        obj.u32('ulNumReverberator')
        for elem in obj.list('pObjects', 'AkDiffuseReverberator', obj.lastval):
            elem.sid('ID').fnv(wdefs.fnv_aco)
            elem.f32('Time')
            elem.f32('HFRatio')
            elem.f32('DryLevel')
            elem.f32('WetLevel')
            elem.f32('Spread')
            elem.f32('Density')
            elem.f32('Quality')
            elem.f32('Diffusion')
            elem.f32('Scale')
    else:
        pass

    return


#******************************************************************************
# ENVS

#026>=
def CAkBankMgr__ProcessEnvSettingsChunk(obj):
    #CAkBankMgr::ProcessEnvSettingsChunk
    obj.set_name('EnvSettingsChunk')
    version = get_version(obj)

    if   version <= 154:
        if   version <= 89:
            max_x = 2
            max_y = 2
        elif version <= 150:
            max_x = 2
            max_y = 3
        else:
            max_x = 4
            max_y = 3

        obj = obj.node('ConversionTable')
        for i in range(max_x):
            for j in range(max_y):
                # CAkEnvironmentsMgr->ConversionTable array
                elem = obj.node('ObsOccCurve[%s][%s]' % (wdefs.eCurveXType.enum[i], wdefs.eCurveYType.enum[j]))
                elem.u8i('bCurveEnabled') #when != 0
                if version <= 36: #36=UFC
                    elem.u32('eCurveScaling').fmt(wdefs.AkCurveScaling)
                    elem.u32('ulCurveSize')
                else:
                    elem.u8i('eCurveScaling').fmt(wdefs.AkCurveScaling)
                    elem.u16('ulCurveSize')
                parse_rtpc_graph(elem, name='aPoints', subname='AkRTPCGraphPoint')
    else:
        obj.tid('attenuationID')


    return


#******************************************************************************
# DIDX

#046>= (034>=)
def CAkBankMgr__LoadMediaIndex(obj):
    #CAkBankMgr::LoadMediaIndex
    obj.set_name('MediaIndex')
    chunk_size = obj.lastval

    uNumMedias = chunk_size // 0x0c
    for elem in obj.list('pLoadedMedia', 'MediaHeader', uNumMedias):
        elem.sid('id').fnv(wdefs.fnv_no)
        elem.U32('uOffset')
        elem.U32('uSize')
    return


#******************************************************************************
# PLAT

#113>=
def CAkBankMgr__ProcessCustomPlatformChunk(obj):
    #CAkBankMgr::ProcessCustomPlatformChunk
    obj.set_name('CustomPlatformChunk')
    version = get_version(obj)

    if version <= 136:
        obj.u32('uStringSize')
        obj.str('pCustomPlatformName', obj.lastval)
    else:
        obj.stz('pCustomPlatformName')

    return


#******************************************************************************
# INIT

#118>=
def CAkBankMgr__ProcessPluginChunk(obj):
    #CAkBankMgr::ProcessPluginChunk
    obj.set_name('PluginChunk')
    version = get_version(obj)

    obj.u32('count')
    for elem in obj.list('pAKPluginList', 'IAkPlugin', obj.lastval):
        parse_plugin(elem)
        if version <= 136:
            #AK::ReadBankStringUtf8
            elem.u32('uStringSize')
            elem.str('pDLLName', elem.lastval)
        else:
            #AK::ReadBankStringUtf8
            elem.stz('pDLLName') #can be null
    return


#******************************************************************************
# chunks

def parse_chunk_default(obj):
    pass

chunk_dispatch = {
    b'BKHD': CAkBankMgr__ProcessBankHeader,
    b'HIRC': CAkBankMgr__ProcessHircChunk,
    b'DATA': CAkBankMgr__ProcessDataChunk,
    b'FXPR': CAkBankMgr__ProcessFxParamsChunk,
    b'ENVS': CAkBankMgr__ProcessEnvSettingsChunk,
    b'STID': CAkBankMgr__ProcessStringMappingChunk,
    b'STMG': CAkBankMgr__ProcessGlobalSettingsChunk,
    b'DIDX': CAkBankMgr__LoadMediaIndex, #034>=
    b'PLAT': CAkBankMgr__ProcessCustomPlatformChunk, #113>=
    b'INIT': CAkBankMgr__ProcessPluginChunk, #118>=
}

def parse_chunk_akbk(obj):
    try:
        obj.four('dwTag').fmt(wdefs.chunk_type)
        obj.U32('unknown')
        obj.U32('unknown')
    except wmodel.ParseError as e:
        obj.add_error(str(e))
    return

def parse_chunk(obj):
    #CAkBankMgr::LoadBank
    chunk = None
    try:
        obj.four('dwTag').fmt(wdefs.chunk_type)
        chunk = obj.lastval
        tag = obj.lastval
        obj.U32('dwChunkSize').omax()

        dispatch = chunk_dispatch.get(tag, parse_chunk_default)
        dispatch(obj)
    except wmodel.ParseError as e:
        obj.add_error(str(e))
    except wio.ReaderError as e:
        raise wio.ReaderError('failed parsing chunk %s' %  (chunk)) from e

    obj.consume()
    return

# #############################################################################

class Parser(object):
    # when loading multiple banks
    MULTIBANK_AUTO          = 'auto'
    MULTIBANK_MANUAL        = 'manual-all'
    MULTIBANK_FIRST         = 'first'
    MULTIBANK_LAST          = 'last'
    MULTIBANK_BIGGEST       = 'biggest'
    MULTIBANK_BIGGEST_LAST  = 'biggest+last'
    MULTIBANK_SMALLEST      = 'smallest'

   #MULTIBANK_NEWEST            = 6 # latest timestamp (useful?)
    MULTIBANK_MODES = [
        MULTIBANK_AUTO,
        MULTIBANK_MANUAL,
        MULTIBANK_FIRST,
        MULTIBANK_LAST,
        MULTIBANK_BIGGEST,
        MULTIBANK_BIGGEST_LAST,
        MULTIBANK_SMALLEST,
    ]

    def __init__(self):
        #self._ignore_version = ignore_version
        self._banks = {}
        self._names = None


    def _check_header(self, r, bank):
        root = bank.get_root()
        current = r.current()

        fourcc = r.fourcc()
        if fourcc == b'AKBK':
            # very early versions have a mini header before BKHD
            _unknown = r.u32() #null
            _unknown = r.u32() #null
            r.guess_endian32(0x10)
            fourcc = r.fourcc()

        if fourcc != b'BKHD':
            raise wmodel.VersionError("%s is not a valid Wwise bank" % (r.get_filename()), -1)

        _size = r.u32()


        version = r.u32()
        if version == 0 or version == 1:
            _unknown = r.u32()
            version = r.u32() #actual version in very early banks

        # strange variations
        if version in wdefs.bank_custom_versions:
            version = wdefs.bank_custom_versions[version]
            root.set_custom(True)

        # 'custom' versions start with bitflag 0x80*
        if version & 0xFFFF0000 == 0x80000000:
            logging.warning("parser: unknown custom version %x, may output errors (report)", version)
            version = version & 0x0000FFFF
            root.set_custom(True)

        # in rare cases header is slightly encrypted with 32b values x4, in the game's init code [LIMBO demo, World of Tanks]
        # simulate with a xorpad file (must start with 32b 0, 32b0 then 32b x4 with xors in bank's endianness)
        if version & 0x0FFFF000:
            path = r.get_path()
            if path:
                path += '/'
            path += 'xorpad.bin'
            try:
                with open(path, 'rb') as f:
                    xorpad = f.read()
            except:
                # too limited to recover
                raise wmodel.VersionError("encrypted bank version (needs xorpad.bin)", -1)
            r.set_xorpad(xorpad)
            r.skip(-4)
            version = r.u32() #re-read unxor'd

        # overwrite for cursom versions
        root.set_version(version)
        if version not in wdefs.bank_versions: #not self._ignore_version and 
            # allow since there shouldn't be that many changes from known versions
            if version <= wdefs.ancient_versions:
                logging.warning("parser: support for version %i is incomplete and may output errors (can't fix)", version)
            else:    
                logging.warning("parser: unknown bank version %i, may output errors (report)", version)
            #raise wmodel.VersionError("unsupported bank version %i" % (version), -1)

        r.seek(current)

        wdefs.setup(version)
        wcls.setup()
        return version

    def parse_banks(self, filenames):
        loaded_filenames = []
        for filename in filenames:
            loaded_filename = self.parse_bank(filename)
            if loaded_filename:
                loaded_filenames.append(loaded_filename)

        logging.info("parser: done")
        return loaded_filenames

    # Parses a whole bank into memory and adds to the list. Can be kinda big (ex. ~50MB in RAM)
    # but since games also load banks in memory should be within reasonable limits.
    def parse_bank(self, filename):
        if filename in self._banks:
            logging.info("parser: ignoring %s (already parsed)", filename)
            return

        logging.info("parser: parsing %s", filename)

        try:
            with open(filename, 'rb') as infile:
                #real_filename = infile.name
                r = wio.FileReader(infile)
                r.guess_endian32(0x04)
                res = self._process(r, filename)

            if res:
                logging.info("parser: %s", res)
                return None

            logging.debug("parser: done %s", filename)
            return filename

        except wio.ReaderError as e:
            error_info = self._print_errors(e)
            logging.error("parser: error parsing %s (corrupted file?), error:\n%s" % (filename, error_info))
            #logging.exception also prints stack trace
        except Exception as e:
            logging.error("parser: error parsing " + filename, e)

        return None

    def _print_errors(self, e):
        import traceback

        # crummy format exception, as python doesn't seem to offer anything decent
        info = []
        trace = traceback.format_exc()
        trace_lines = trace.split('\n')
        trace_lines.reverse()
        for line in trace_lines:
            target_msg = 'Error: '
            if target_msg in line:
                index = line.index(target_msg) + len(target_msg)
                exc_info = '%s- %s' % ('  ' * len(info), line[index:])
                info.append(exc_info)

        #[exceptions.append(line) for line in msg_list if line.startswith('Exception:')]
        text = '\n'.join(info)
        return text

    def _process(self, r, filename):
        bank = wmodel.NodeRoot(r)

        try:
            version = self._check_header(r, bank)

            # first chunk in ancient versions doesn't follow the usual rules
            if version <= 14:
                obj = bank.node('chunk')
                parse_chunk_akbk(obj)

            while not r.is_eof():
                obj = bank.node('chunk')
                parse_chunk(obj)

        except wmodel.VersionError as e:
            return e.msg
        #other exceptions should be handled externally
        #except wmodel.ParseError as e:
            #bank.add_error(str(e))

        if bank.get_error_count() > 0:
            logging.info("parser: ERRORS! %i found (report issue)" % bank.get_error_count())
        if bank.get_skip_count() > 0:
            logging.info("parser: SKIPS! %i found (report issue)" % bank.get_skip_count())

        if self._names:
            bank.set_names(self._names)

        root = bank.get_root()
        sid = root.get_id()
        lang = root.get_lang()
        size = r.get_size()

        self._banks[filename] = (bank, sid, lang, size)
        return None

    def get_banks(self, mode=None):
        if not mode:
            mode = self.MULTIBANK_AUTO

        if mode not in self.MULTIBANK_MODES:
            logging.warning("parser: WARNING, unknown repeat mode '%s'" % (mode))
            
        # as loaded (MULTIBANK_ALLOW_MANUAL)
        items = self._banks.values()

        done = {}
        banks = []
        for bank, version, lang, size in items:

            key = (version, lang)
            if key not in done:
                # not a dupe = always include
                done[key] = (bank, size)
                banks.append(bank)
                continue

            # handle dupe
            old_bank, old_size = done.get(key)
            index = banks.index(old_bank)


            # allow as loaded
            if mode == self.MULTIBANK_MANUAL:
                banks.append(bank)

            # allow, bigger first
            if mode == self.MULTIBANK_AUTO:
                if size > old_size:
                    banks.insert(index, bank) #before
                else:
                    banks.append(bank) #after (tail)
               
            # ignore current
            if mode == self.MULTIBANK_FIRST:
                pass

            # overwrite old
            if mode == self.MULTIBANK_LAST:
                banks[index] = bank
                done[key] = (bank, size)

            # favor bigger
            if mode == self.MULTIBANK_BIGGEST:
                if size > old_size:
                    banks[index] = bank #overwrite
                    done[key] = (bank, size)

            # favor bigger, or last (same size = overwrite)
            # (generally useless except when fine-tuning which clone banks are preferred, for -fc + multiple updates)
            if mode == self.MULTIBANK_BIGGEST_LAST:
                if size >= old_size:
                    banks[index] = bank #overwrite
                    done[key] = (bank, size)

            # favor smaller
            if mode == self.MULTIBANK_SMALLEST:
                if size < old_size:
                    banks[index] = bank #overwrite
                    done[key] = (bank, size)

        return banks

    def get_filenames(self):
        return list(self._banks.keys())

    def set_names(self, names):
        self._names = names
        for items in self._banks.values():
            bank = items[0]
            bank.set_names(names)

    #def set_ignore_version(self, value):
    #    self._ignore_version = value

    def unload_bank(self, filename):
        if filename not in self._banks:
            logging.warning("parser: can't unload " + filename)
            return

        logging.info("parser: unloading " + filename)
        self._banks.pop(filename)
