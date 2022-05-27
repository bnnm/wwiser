
_WARN_PROPS = [
    #"[FadeInCurve]", "[FadeOutCurve]", #seen in CAkState, used in StateChunks (ex. NSR)
    #"[TrimInTime]", "[TrimOutTime]", #seen in CAkState (ex. DMC5)
    "[FadeInTime]", "[FadeOutTime]",
    "[CrossfadeUpCurve]", "[CrossfadeDownCurve]", "[LoopCrossfadeDuration]",
    "[LoopStart]", "[LoopEnd]",
]


# "behavior" field props (shown in path tree)
_FIELD_BEHAVIOR_PROPS = {
    '[Loop]', '[DelayTime]', '[InitialDelay]'
}

# fields props for statechunk info (most others aren't interesting for txtp purposes)
_FIELD_REGISTER_PROPS = {
    '[Volume]','[LFE]','[Pitch]','[LPF]','[HPF]','[BusVolume]','[MakeUpGain]',
    '[PAN_LR]','[PAN_FR]','[CenterPCT]','[DelayTime]','[TransitionTime]','[Probability]',
    '[OutputBusVolume]','[OutputBusHPF]','[OutputBusLPF]',
    '[LoopStart]','[LoopEnd]', '[TrimInTime]','[TrimOutTime]',
    '[FadeInTime]','[FadeOutTime]', '[FadeInCurve]','[FadeOutCurve]',
    '[LoopCrossfadeDuration]', '[CrossfadeUpCurve]','[CrossfadeDownCurve]',
    '[PlaybackSpeed]','[Loop]','[InitialDelay]','[PAN_UD]',
}

_OLD_AUDIO_PROPS = [
    ('Volume', 'Volume.min', 'Volume.max'),
    ('LFE', 'LFE.min', 'LFE.max'),
    ('Pitch', 'Pitch.min', 'Pitch.max'),
    ('LPF', 'LPF.min', 'LPF.max'),
]

_OLD_ACTION_PROPS = [
    ('tDelay', 'tDelayMin', 'tDelayMax'),
    ('TTime', 'TTimeMin', 'TTimeMax'),
]

_OLD_TRANSLATION_PROPS = {
    'tDelay': 'DelayTime',
    'TTime': 'TransitionTime',
}

# Extra info on some props:
# - MakeUpGain: secondary volume value, where first you set a "HDR window" in the container bus,
#   and sounds volumes are altered depending on window and MakeUpGain (meant for temp focus on some sfxs).
#   When HDR window has default settings it seems to behave like regular volume (ex. Gunslinger Stratos).
# - Delay/InitialDelay is the time between the object is reached and it starts to play.
#   Both only differ on where are used (Delay=actions, InitialDelay=audio), while music hierarchy doesn't
#   use them as it has clips. Only applies when an object is actually played again:
#   - ranseq loop=inf + aksound idelay=1, loop=--- > each loop has 1 sec delay (aksound is played many times)
#   - ranseq loop=--- + aksound idelay=1, loop=inf > only first play has 1 sec delay (aksound loops don't count as replaying)

class CAkProps(object):
    def __init__(self, node):
        self.valid = False

        # relative
        self.volume = 0 #main "voice" volume (objects) or volume added to input voices (bus)
        self.busvolume = 0 #main volume for the bus itself (bus only)
        self.outputbusvolume = 0 #volume used when passing to a main bus (aux-buses have their own)
        self.makeupgain = 0 #special volume added to voice volume (objects)
        self.pitch = 0
        self.playbackspeed = 0 #multiplicative!
        # absolute
        # (could handle positioning params)
        # behavior
        self.delay = 0
        self.loop = None

        self._props = {} #name > value
        self._ranges = {} #name > (min, max)

        # external info
        self.unknowns = []
        # default/all
        self.fields_fld = [] #single field
        self.fields_std = [] # key-val
        self.fields_rng = [] # key-min/max
        # behavior props
        self.fields_bfld = self.fields_fld
        self.fields_bstd = []
        self.fields_brng = []

        self._build(node)

    def _build(self, node):
        # props are a list of values or ranged values.
        # newer wwise use 2 lists (both should exist even if empty), while
        # older wwise use regular fields as properties, that vary a bit
        # props are valid once at least one is found.
        self._build_new(node)
        self._build_old(node)
        # change generic list into usable one
        self._prepare()

    
    def _prepare(self):
        self.loop = self._prop('[Loop]', default=None) #loop 0 = infinite

        self.volume = self._prop('[Volume]')
        self.makeupgain = self._prop('[MakeUpGain]')
        self.busvolume = self._prop('[BusVolume]')
        self.outputbusvolume = self._prop('[OutputBusVolume]')

        self.pitch = self._prop('[Pitch]') #for sound hierarchy
        self.playbackspeed = self._prop('[PlaybackSpeed]') #for music hierarchy

        var1 = self._prop('[DelayTime]') #in actions
        var2 = self._prop('[InitialDelay]') #in actor-mixer hierarchy
        if var1 and var2:
            raise ValueError("2 delays found")
        if var2:
            var1 = var2 * 1000.0 #idelay is float in seconds to ms
        self.delay = var1

        # missing useful effects:
        #HPF
        #LPF
        #PAN_LR: seems to change voice LR
        #PAN_FR: seems to change voice FR?
        #TransitionTime: action fade-in time (also has a PlayActionParams > eFadeCurve)
        #Probability: used in play events to fade-in event
        #CenterPCT: not useful?
        #Duration? for crossfades?

    def is_usable(self, apply_bus):
        if apply_bus and (self.busvolume or self.outputbusvolume):
            return True
        return self.loop is None or self.volume or self.makeupgain or self.delay

    def _prop(self, name, default=0):
        value = self._props.get(name)
        minmax = self._ranges.get(name)
        if value is None and minmax is None:
            return default

        if value is None:
            value = 0
        # try average
        if minmax:
            vmin, vmax = minmax
            if vmin or vmax: #don't average if both are 0
                min = value + vmin
                max = value + vmax
                value = (min + max) / 2

        return value

    def _keyname(self, nkey):
        keyname = nkey.get_attr('valuefmt') # "0xNN [name]"

        # by default keyname is "0xNN [thing]", change to "[thing]"
        # but not for unknown values, as text may not be unique ("[?]")
        if '?' not in keyname and 'Custom' not in keyname:
            pos = keyname.index('[')
            keyname = keyname[pos:]

        return keyname

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

                keyname = self._keyname(nkey)
                pval = nval.value()
                self._add_prop(self._props, keyname, pval)

                if keyname not in _FIELD_REGISTER_PROPS:
                    continue
                item = (nkey, nval)
                self.fields_std.append(item)
                if not _FIELD_BEHAVIOR_PROPS or keyname in _FIELD_BEHAVIOR_PROPS:
                    self.fields_bstd.append(item)


        # ranged values, wwise picks one value at random on each play
        nranges = node.find(name='AkPropBundle<RANGED_MODIFIERS<AkPropValue>>')
        if nranges:
            self.valid = True
            nprops = nranges.finds(name='AkPropBundle')
            for nprop in nprops:
                nkey = nprop.find(name='pID')
                nmin = nprop.find(name='min')
                nmax = nprop.find(name='max')

                keyname = self._keyname(nkey)
                rval = (nmin.value(), nmax.value())
                self._add_prop(self._ranges, keyname, rval)

                if keyname not in _FIELD_REGISTER_PROPS:
                    continue
                item = (nkey, nmin, nmax)
                self.fields_rng.append(item)
                if not _FIELD_BEHAVIOR_PROPS or keyname in _FIELD_BEHAVIOR_PROPS:
                    self.fields_brng.append(item)


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
            self._build_old_props(naudio, _OLD_AUDIO_PROPS)
        if naction:
            self._build_old_props(naction, _OLD_ACTION_PROPS)


    # old props are simpler, but we can simulate newer props
    def _build_old_props(self, nbase, proplist):
        if not nbase:
            return
        self.valid = True

        for keybase, keymin, keymax in proplist:
            nprop = nbase.find(name=keybase)
            if not nprop:
                continue
            nmin = nbase.find(name=keymin)
            nmax = nbase.find(name=keymax)

            self.fields_fld.extend([nprop, nmin, nmax])

            keyname = "[%s]" % (_OLD_TRANSLATION_PROPS.get(keybase, keybase)) #transform in some cases
            pval = nprop.value()
            mval = (nmin.value(), nmax.value())
            self._add_prop(self._props, keyname, pval)
            self._add_prop(self._ranges, keyname, mval)


    def _add_prop(self, items, keyname, val):
        if any(prop in keyname for prop in _WARN_PROPS):
            self.unknowns.append(keyname)

        if keyname in items:
            raise ValueError("repeated prop " + keyname)
        items[keyname] = val

    # external in some cases, unifies handling
    def set_loop(self, value, min=None, max=None):
        key = '[Loop]'
        self._props[key] = value
        if min is not None and max is not None:
            self._ranges[key] = (min, max)

        self.loop = self._prop(key, default=None)
        return

    # messes up calculations in some cases
    def disable_loop(self):
        self.loop = None
        pass

    # unknown meaning in some cases
    def barf_loop(self):
        if self.loop is not None:
            raise ValueError("loop flag found")
