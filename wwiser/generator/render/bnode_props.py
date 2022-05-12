

_WARN_PROPS = [
    #"[TrimInTime]", "[TrimOutTime]", #seen in CAkState (ex. DMC5)
    #"[FadeInCurve]", "[FadeOutCurve]", #seen in CAkState, used in StateChunks (ex. NSR)
    "[LoopStart]", "[LoopEnd]",
    "[FadeInTime]", "[FadeOutTime]", "[LoopCrossfadeDuration]",
    "[CrossfadeUpCurve]", "[CrossfadeDownCurve]",
    #"[MakeUpGain]", #seems to be used when "auto normalize" is on (ex. Magatsu Wahrheit, MK Home Circuit)
    #"[BusVolume]", #percent of max? (ex. DmC)
    #"[OutputBusVolume]"
]

_OLD_AUDIO_PROPS = [
    'Volume', 'Volume.min', 'Volume.max', 'LFE', 'LFE.min', 'LFE.max',
    'Pitch', 'Pitch.min', 'Pitch.max', 'LPF', 'LPF.min', 'LPF.max',
]
_OLD_ACTION_PROPS = [
    'tDelay', 'tDelayMin', 'tDelayMax', 'TTime', 'TTimeMin', 'TTimeMax',
]

#TODO missing useful effects:
#HPF
#LPF
#PAN_LR: seems to change voice LR
#PAN_FR: seems to change voice FR?
#TransitionTime
#Probability: used in play events to fade-in event
#CenterPCT: not useful?

#PROP_LOOP = "[Loop]"


class CAkProps(object):
    def __init__(self, node):
        self.valid = False

        self.loop = None
        self.volume = None
        self.makeupgain = None
        self.pitch = None
        self.delay = None
        self.idelay = None
        
        self.unknowns = []
        self.fields_std = []
        self.fields_rng = []

        self._build(node)

    def _build(self, node):

        #newer to older types
        nbundles = node.find(name='AkPropBundle<AkPropValue,unsigned char>')
        if not nbundles:
            nbundles = node.find(name='AkPropBundle<float,unsigned short>')
        if not nbundles:
            nbundles = node.find(name='AkPropBundle<float>')

        # standard values if set
        if nbundles:
            self.valid = True
            nprops = nbundles.finds(name='AkPropBundle')
            for nprop in nprops:
                nkey = nprop.find(name='pID')
                nval = nprop.find(name='pValue')

                valuefmt = nkey.get_attr('valuefmt')
                value = nval.value()
                if any(prop in valuefmt for prop in _WARN_PROPS):
                    self.unknowns.append(valuefmt)

                elif "[Loop]" in valuefmt:
                    self.loop = value

                elif "[Volume]" in valuefmt:
                    self.volume = value

                elif "[MakeUpGain]" in valuefmt:
                    self.makeupgain = value

                elif "[Pitch]" in valuefmt:
                    self.pitch = value

                elif "[DelayTime]" in valuefmt:
                    self.delay = value

                elif "[InitialDelay]" in valuefmt:
                    self.idelay = value * 1000.0 #float in seconds to ms

                self.fields_std.append( (nkey, nval) )

        #TODO
        # ranged values, wwise picks one value at random on each play
        nranges = node.find(name='AkPropBundle<RANGED_MODIFIERS<AkPropValue>>')
        if nranges:
            self.valid = True
            nprops = nranges.finds(name='AkPropBundle')
            for nprop in nprops:
                nkey = nprop.find(name='pID')
                nmin = nprop.find(name='min')
                nmax = nprop.find(name='max')

                self.fields_rng.append( (nkey, nmin, nmax) )

class CAkActionProps(object):
    pass

class CAkStateProps(object):
    pass

class CAkNodeProps(object):
    pass
