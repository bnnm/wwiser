

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
#PlaybackSpeed: similar to pitch but for music hierarchy (pitch should be ignored by music), "multiplied by ancestors"
#PROP_LOOP = "[Loop]"

#delays: not inherited
#- InitialDelay: how long to wait until playing some song
#  - if changed with an schunk while song is playing it has no effect
#- DelayTime: "delay" in editor, time to trigger an action

# on actions:
# TransitionTime: fade-in time (also has a PlayActionParams > eFadeCurve)
#

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
        self.fields_fld = []
        self.fields_std = []
        self.fields_rng = []

        self._build(node)

    def _build(self, node):
        # props are a list of values or ranged values.
        # newer wwise use 2 lists (both should exist even if empty), while
        # older wwise use regular fields as properties, that vary a bit
        # props are valid once at least one is found.
        self._build_new(node)
        self._build_old(node)


    def _build_new(self, node):

        # standard values (newer to older)
        nbundles = node.find(name='AkPropBundle<AkPropValue,unsigned char>')
        if not nbundles:
            nbundles = node.find(name='AkPropBundle<float,unsigned short>')
        if not nbundles:
            nbundles = node.find(name='AkPropBundle<float>')
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

                elif "[Pitch]" in valuefmt: #for sound hierarchy
                    self.pitch = value
                #PlaybackSpeed for music hierarhcy

                elif "[DelayTime]" in valuefmt: #for actions
                    self.delay = value

                elif "[InitialDelay]" in valuefmt: #for audio
                    self.idelay = value * 1000.0 #float in seconds to ms

                self.fields_std.append( (nkey, nval) )


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

    def _build_old(self, node):
        if self.valid:
            return

        # only one should exist
        naudio = None
        naction = None

        if node.get_name() == 'NodeInitialParams':
            naudio = node
        elif node.get_name() == 'ActionInitialValues':
            naction = node
        else:
            naudio = node.find1(name='NodeInitialParams')
            if not naudio:
                naction = node.find1(name='ActionInitialValues')

        if naudio:
            self._build_old_audionode(naudio)
        if naction:
            self._build_old_actionnode(naction)

    def _build_old_actionnode(self, nbase):
        if not nbase:
            return
        self.valid = True

        #may use PlayActionParams + eFadeCurve when TransitionTime is used to make a fade-in (goes after delay)

        for prop in _OLD_ACTION_PROPS:
            nprop = nbase.find(name=prop)
            if not nprop:
                continue
            value = nprop.value()
            if value == 0:
                continue

            #if prop == 'TTime' or prop == 'TTimeMin': #fade-in curve
            #    self._barf("found " + prop)

            if prop == 'tDelay' or prop == 'tDelayMin':
                self.idelay = value

            self.fields_fld.append(nprop)


    def _build_old_audionode(self, nbase):
        if not nbase:
            return
        self.valid = True

        for prop in _OLD_AUDIO_PROPS:
            nprop = nbase.find(name=prop)
            if not nprop:
                continue
            value = nprop.value()
            if value == 0:
                continue

            if prop == 'Volume':
                self.volume = value
            #TODO min/max

            self.fields_fld.append(nprop)


    def has_volumes(self):
        return self.volume or self.makeupgain
