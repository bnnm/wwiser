from ..txtp import hnode_misc

_DEBUG_SIMPLER_PROPS = False # calculate like old wwiser versions (enables some flags + ignores buses)


# PROPERTY CALCULATIONS
#
# Wwise objects have associated "properties" (volumes, delays, pitch, etc), but the way final
# values are calculated is rather complex. Objects are part of a hierarchy (parents) and
# properties "trickle down" differently depending on their type:
# - "relative" properties (volume, pitch, lfo, etc): final value adds from all parents
# - "absolute" properties (bus, positioning, etc): first value found (current object may overwrite parent)
# - "behavior" properties (loops, delays, etc): only used when event chain passes over those objects
# (not an official classification)
#
# "Relative" and "absolute" properties are taken from current and parent objects, even if an event chain
# doesn't 'use' said parents, while "behavior" properties's meaning are usually object-dependant 
# (doesn't make sense to inherit a loop flag).
#
# For example with a "family" of aksound >> switch >> actor-mixer the aksound inherits properties from
# both ancestors (even if actor-mixers aren't part of events). This way one can make hierarchies and change
# multiple children's properties at once (setting the actor-mixer's volume).
#
# If some part of the family has properties that change via statechunk/rtpc, and are active, they are
# taken into account when calculating object's properties. Each only allows changing some types of
# properties though.
#
#
# BUSES
# Apart from their inheritance, "audible" (.wem) objects 'pass through' an assigned "bus" ("absolute" prop).
# Buses in turn have and inherit properties that are then applied to the object. These props are
# separate so you can route an object through buses with distinct effects and config without having to
# change the object directly. Buses can't have "behavior" properties (to create a "delay" prop would
# need to use "effects").
#
# Multiple objects may override bus, but only first defined one is used and rest would be ignored.
# - ranseq [master-bus] > aksound [(no bus)] 
# - ranseq [master-bus] > aksound [music-bus]
# In the first case, aksound uses master-bus's props, but in the second only music-bus is used.
# (if master-bus has -96db, aksound will be silent in the first case, not in the second).
#
# Objects may set special bus props (OutputBusVolume/HPF/HPF) which only apply to the *directly* overriden bus.
#   > ranseq   OutpuBusVolume = -5db        OverrideID=music-bus
#     > segment   OutpuBusVolume = -10db        OverrideID=master-bus
# In the example only -10db is applied (not -15db). If segment removes OverrideBusId it would use -5db
# by inheriting bus + applying parent's props, but OutputBusVolume may still be defined in segment
# (the Wwise editor internally hides -10db if override is unset, shows -10db again if set).
# OutputBusVolume set via RTPC or states also matter.
# Note that buses also have OutputBusVolume which is inherited from parents and applied normally.
#
# Generally bus volumes aren't too important since final volume can be autonormalized, but in
# odd cases buses are used to fix certain .wem volumes and may contain useful statechunks
# (seen in Astral Chain wems with  "low" "mid" buses + silence states).
#
#
# EXAMPLE
# - object hierarchy                                     - bus hierarchy
#   actormixer {vol +2db} [bus=master_bus]                 bgm_bus { vol +1db }
#       > statechunk: bgm=hi > vol = +3db                    master_bus { vol -3db }
#     ranseq {delay +2} [bus=sound_bus]                    sound_bus { vol +2db }
#       switch {vol 0db, delay +1} [bus=bgm_bus]
#         aksound {vol -1db} [bus=0]
#
# - with an event > actionplay > aksound, calculations are:
#   * aksound's family props: { vol -1+0+0+2 = +1db }
#     > ranseq's delay is an "absolute" prop = not inherited
#   * aksound's bus=0 > inherit ancestor's first valid bus: bgm_bus
#   * bus_output's family props: { vol +1-3 = -2db }
#   * aksound final props: { vol +1-2db = -1db }
#   * if we set state bgm=hi, also inherits +3db from the actormixer
#
# - with an event > actionplay > ranseq
#   * ranseq: apply delay 2
#     > non-audio objects don't pass over busses, so sound_bus's vol isn't used
#   * switch: apply delay 1
#     > bgm_bus props also don't apply
#   * aksound: calc final props like before
#     > by following this path, aksound has delay 2+1 (plus its own delay if any is set)
#
# Resulting properties are clamped to valid min/max, depending on type.
# Some properties have special meanings and are applied at different points (for example
# there are "Volume", "MakeUpGain", "OutputBusVolume", "BusVolume", etc) but ultimately
# are added the final value (in simpler cases, see below).
#
#
# BUS TYPES
# Buses actually come in two forms:
# - non-mixing: properties are passed down to the objects
# - mixing: does processing then applies (some) properties
#   - BusVolume/OutputBusVolume are post applied, Volume/MakeUpGain are still passed down
# A bus becomes "mixing" when does anything that would alter the audio buffers: aux/hdr bus, has effects (even
# if bypassed), has positioning, changes channels (down/upmixing), RTPC on BusVolume/OutputBusVolume/LPF/HPF, etc.
# Buses on top (master) are also mixing, since they make final output.
#
# Basically Wwise tries to pass "voices" (individual .wem buffers) around and applying props at once and mixing as
# late as possible, then creating a "main mix" or final N.Nch buffer, before # sending to the endpoint (platform's
# audio out). But if a bus modifies audio signal, can't add certain props or meaning changes:
# - doing -2db, then -2db == doing -4db once (so it's faster done once)
# - doing -2db, eq+reverb, -2db != doing -4db, eq+reverb
#
# Example:
#   123.wem: +1db VoiceVolume
#       stage_bus: { +2db BusVolume, +3 OutputBusVolume }               (non-mixing)
#           bgm_bus: {effect=reverb, +4db VoiceVolume, +5db BusVolume}  (mixing due to effect)
#              main_bus: { +6db VoiceVolume, +7db BusVolume}             (non-mixing)
#                  master_bus: {+8db BusVolume}                         (mixing due to master)
#   * apply voice volumes: 1+4+6=11 and 2+3 (*any* VoiceVolumes in chain, and bus props until next mixing bus)
#   * apply effect + bus volumes: 5 and 7 (bus props until next mixing bus)
#   * apply bus volumes: 8 + final output (N.N audio), total 36db
#
# Latest Wwise versions also separate mixing buses into 3 subtypes depending on if the bus mixes voices or applies
# effects over individual wem, though some effects are ignored ("peak limiter" is unrealiable per wem or reverb
# would be slow).
#
# The calculations below treat all buses as non-mixing (adds all props once), since we can't apply effects, though
# results should be reasonably close.


# relative props are only added when node is an actual sound output object
_HIRC_AUDIBLE = {
    'CAkSound',
    'CAkMusicTrack'
}

# Objects that may contain useful statechunks/rtpcs. Mainly useful on "playable audio" level,
# on parents usually just silence the base song in various ways.
# (leave empty to include all, but sometimes makes humongous number of combos)
# This is only for detection+report combos, states/gamevars are applied if set.
_HIRC_COMBOS_STATECHUNKS = {
    'CAkSound',
    'CAkMusicTrack',
    'CAkMusicSegment',
}
_HIRC_COMBOS_RTPCS = {
    'CAkSound',
    'CAkMusicTrack',
    'CAkMusicSegment',
}


_CLAMP_LOOPS = (0, 32767) # number
_CLAMP_VOLUME = (-200.0, 200.0) # db
_CLAMP_DELAY = (0 * 1000.0,  3200 * 1000.0) # seconds to ms
#_CLAMP_FILTER = (0, 100) # percent (for HPF/LPF)
_VOLUME_SILENT = -96.0


# take a HIRC node and return calculated config based on all props from current and parents
class PropertyCalculator(object):
    def __init__(self, ws, bnode, txtp):
        self._ws = ws
        self._bnode = bnode
        self._txtp = txtp
        self._config = hnode_misc.NodeConfig()

        self._hirc_audible = bnode.name in _HIRC_AUDIBLE
        self._include_fx = txtp.txtpcache.x_include_fx #probably ok but not very tested

        # process flags
        self._is_base_object = None 
        self._is_bus_holder = None
        self._is_processing_bus = False
        self._uses_vars = False #if applies statechunk/gamevars


    def get_properties(self):
        if _DEBUG_SIMPLER_PROPS:
            self._hirc_audible = True

        # load if possible (only audible nodes use buses)
        self._bus = BusLoader(self._bnode, self._hirc_audible)

        # add props from current objects and its parents
        # (base node gets behavior props, and relative only if it's audible)
        self._calculate_props(self._bnode)

        # add props from bus and its parents, similar to the above with small differences
        # will also register rtpcs and statechunk combos while reading props (may be repeated)
        # (buses can't apply certain props like delays, but shouldn't be found anyway)
        if self._bus:
            self._is_processing_bus = True
            self._calculate_props(self._bus.bbus)
            self._is_processing_bus = False

        # cleanup
        pproc = PropertyPostprocessor(self._config)
        pproc.clamp()
        pproc.mark_flags(self._uses_vars)

        return self._config

    # -------------------------------------------------------------------------

    # apply all properties for a node
    def _calculate_props(self, bnode):
        if not bnode:  #no parent
            return

        if not self._is_processing_bus:
            # base node applies extra props that aren't inherited
            self._is_base_object = self._bnode == bnode
            # current node applies extra bus props
            self._is_bus_holder = self._bus.bholder == bnode

        self._apply_props(bnode.props)
        self._apply_props_fx(bnode)

        self._apply_statechunks(bnode)
        self._apply_rtpclist(bnode)

        # repeat with parent nodes to simulate prop inheritance (non-playable nodes don't inherit directly)
        if self._hirc_audible and not _DEBUG_SIMPLER_PROPS:
            self._calculate_props(bnode.bparent)

    # -------------------------------------------------------------------------

    # standard props
    def _apply_props(self, props):
        if not props:  #events don't have props
            return

        cfg = self._config

        # behavior props: only on base node
        # (props from statechunks/rtpcs are included, so must add to existing values)
        if self._is_base_object:
            if cfg.loop is None: #statechunks can't have this though
                cfg.loop = props.loop
            cfg.delay += props.delay

        # absolute props: first found only?
        # ...

        # relative props: only add current if base node will output audio
        if self._hirc_audible:
            # sound object volumes
            cfg.gain += props.volume
            cfg.gain += props.makeupgain

            # bus's extra volumes props when "outputting through a bus"
            if self._is_processing_bus:
                cfg.gain += props.busvolume
                cfg.gain += props.outputbusvolume

            # overriden bus's "holder" volumes
            if self._is_bus_holder:
                cfg.gain += props.outputbusvolume


    # standard props
    def _apply_props_fx(self, bnode):
        if not bnode:
            return
        if not self._include_fx:
            return

        cfg = self._config

        # relative props: only add current if base node will output audio
        if self._hirc_audible:
            # fake a bit FX to include Wwise Gain (effects render a bit different but should be ok for typical usage)
            # (may be on bus or node level)
            fxlist = self._get_fxlist(bnode)
            if fxlist:
                gain = fxlist.get_gain()
                cfg.gain += gain
                #TODO handle statechunks/rtpcs in the fxgain

    def _get_fxlist(self, bnode):
        if not bnode:
            return None
        
        if bnode.fxlist:
            return bnode.fxlist
        
        return self._get_fxlist(bnode.bparent)

    # -------------------------------------------------------------------------

    # some objects have state = props in the statechunk, and if we have set those states we want the values
    def _apply_statechunks(self, bnode):
        if not bnode.statechunk:
            return
        cfg = self._config
        ws = self._ws

        check_info = True # always?
        if check_info:
            bscis = bnode.statechunk.get_usable_states(self._is_processing_bus)

            # useful? may mark lots of uninteresting {s}
            #if len(bscis) > 0:
            #    cfg.crossfaded = True

            # register info list and possible combo states while we are at it
            include_combo = not _HIRC_COMBOS_STATECHUNKS or bnode.name in _HIRC_COMBOS_STATECHUNKS
            for bsci in bscis:
                self._txtp.info.report_statechunk(bsci)

                if ws.sc_registrable() and include_combo:
                    item = (bsci.nstategroupid, bsci.nstatevalueid)
                    ws.scpaths.add(*item)

                if include_combo:
                    # mark audio can be modified (technically could be delay only so maybe shouldn't be 'crossfades')
                    cfg.crossfaded = True

        # during register phase no need to apply
        if ws.sc_registrable():
            return
        # find currently set states (may be N)
        for state in ws.scparams.get_states():
            bsi = bnode.statechunk.get_bsi(state.group, state.value)
            if not bsi or not bsi.props:
                continue

            cfg.crossfaded = True
            self._uses_vars = True
            self._apply_props(bsi.props)
            self._txtp.info.statechunk(state)

    # -------------------------------------------------------------------------

    # some objects have rtpc > new value info that can be optionally applied
    def _apply_rtpclist(self, bnode):
        if not bnode.rtpclist:
            return
        cfg = self._config
        gvparams = self._ws.gvparams


        check_info = True # always?
        if check_info:
            brtpcs = bnode.rtpclist.get_usable_rtpcs(self._is_processing_bus)

            # useful? may mark lots of uninteresting {s}
            #if len(brtpcs) > 0:
            #    cfg.crossfaded = True

            include_combo = not _HIRC_COMBOS_RTPCS or bnode.name in _HIRC_COMBOS_RTPCS
            for brtpc in brtpcs:
                self._txtp.info.report_rtpc(brtpc)

                if not gvparams and include_combo:
                    # no autocombos for GVs since thet need careful consideration by users
                    pass

                if include_combo:
                    # mark audio can be modified (technically could be delay only so maybe shouldn't be 'crossfades')
                    cfg.crossfaded = True


        # get currently set rtpcs (may be N)
        if not gvparams:
            return
        for gvitem in gvparams.get_items():
            if not gvitem.key: #special meaning of set all to gvitem's value
                brtpcs = bnode.rtpclist.get_rtpcs()
            else:
                brtpc = bnode.rtpclist.get_rtpc(gvitem.key)
                brtpcs = [brtpc]

            for brtpc in brtpcs:
                if not brtpc or not brtpc.is_usable(self._is_processing_bus):
                    continue

                cfg.crossfaded = True
                self._apply_rtpc(gvitem, brtpc)

    def _apply_rtpc(self, gvitem, brtpc):

        if gvitem.is_default:
            value_x = brtpc.default_x
        elif gvitem.is_min:
            value_x = brtpc.min_x
        elif gvitem.is_max:
            value_x = brtpc.max_x
        else:
            value_x = gvitem.value

        if value_x is None: #not found or not set
            return
        self._uses_vars = True

        value_y = brtpc.get(value_x)

        #TODO improve (maybe rtpc should return some mini props?)
        # apply props
        cfg = self._config

        # behavior props: only on base node
        if self._is_base_object:
            # RTPCs can't have loops
            if brtpc.is_delay:
                cfg.delay = brtpc.accum(value_y, cfg.delay)

        # absolute props: first found only?
        # ...

        # relative props: only add current if base node will output audio
        if self._hirc_audible:
            if brtpc.is_volume:
                cfg.gain = brtpc.accum(value_y, cfg.gain)
            if brtpc.is_makeupgain:
                cfg.gain = brtpc.accum(value_y, cfg.gain)

            if self._is_processing_bus:
                if brtpc.is_busvolume:
                    cfg.gain = brtpc.accum(value_y, cfg.gain)
                if brtpc.is_outputbusvolume:
                    cfg.gain = brtpc.accum(value_y, cfg.gain)

            if self._is_bus_holder:
                if brtpc.is_outputbusvolume:
                    cfg.gain = brtpc.accum(value_y, cfg.gain)


        self._txtp.info.gamevar(brtpc.nid, value_x)

class PropertyPostprocessor(object):
    def __init__(self, config):
        self._config = config

    # props are clamped in Wwise to certain min/max
    def clamp(self):
        self._clamp_config(self._config)

    def mark_flags(self, uses_vars):
        # special flag
        if not uses_vars and self._config.gain <= -96.0:
            self._config.silenced_default = True
        self._config.silenced = self._config.gain <= -96.0

    @staticmethod
    def _clamp_config(cfg):

        # simulate Wwise's clamps, useless but might as well
        cfg.loop = PropertyPostprocessor._clamp_prop(cfg.loop, *_CLAMP_LOOPS)
        cfg.gain = PropertyPostprocessor._clamp_prop(cfg.gain, *_CLAMP_VOLUME)
        cfg.delay = PropertyPostprocessor._clamp_prop(cfg.delay, *_CLAMP_DELAY)

    @staticmethod
    def _clamp_prop(prop, min, max):
        if prop is None:
            return prop
        if prop < min:
            return min
        if prop > max:
            return max
        return prop



# Get output bus if any, since it modifies calculated volume.
# If bus objects can't be found (usually in init.bnk) they simply won't be applied.
class BusLoader(object):
    def __init__(self, bnode, hirc_audible):
        self.bbus = None
        self.bholder = None
        self.loaded = False
        self._hirc_audible = hirc_audible

        self._find_bus(bnode)

        # if buses aren't loaded shouldn't apply buses' properties (like busvolume)
        self.loaded = self.bbus is not None

    def _find_bus(self, bnode):
        if _DEBUG_SIMPLER_PROPS:
            return
        if not self._hirc_audible:
            return

        # get this object's output bus (inherited from ancestor or overriden in current object).
        # the bus's "holder" bnode also applies certain values to the bus
        result = self._get_bus(bnode)
        if result:
            self.bbus = result[0]
            self.bholder = result[1]
            self.aux = result[2]

    @staticmethod
    def _get_bus(bnode):
        if not bnode:
            return None

        if bnode.bbus:
            #TODO improve: should select between object bus or current aux bus when doing calculate
            # need to use aux bus in rare cases. In Elden Ring:
            # - bgm field/battle musictrack variations go to a field bus
            # - field bus uses BusVolume -96db, but defines 2 FieldBattleAux/FieldNormalAux aux buses
            # - both have regular volume and parent is also field's parent
            # So to avoid silent files due to bus volume, detect if we should use aux bus
            if BusLoader.is_bus_usable(bnode.bbus):
                return (bnode.bbus, bnode, False)

            if not bnode.bbus.auxlist:
                return None

            bauxs = bnode.bbus.auxlist.get_bauxs()

            for baux in bauxs:
                # maybe should check best aux based on rtpc/statechunk props but for now just pick first
                if BusLoader.is_bus_usable(baux):
                    return (baux, bnode, True)
            return None
            
        return BusLoader._get_bus(bnode.bparent)

    @staticmethod
    def is_bus_usable(bbus):
        if not bbus or not bbus.props:
            return False
        return bbus.props.busvolume > _VOLUME_SILENT and bbus.props.outputbusvolume > _VOLUME_SILENT
