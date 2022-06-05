from ..txtp import hnode_misc

# PROPERTY CALCULATIONS
#
# Wwise objects have a list of associated "properties" (volumes, delays, pitch, etc), but the way
# final values are calculated is rather complex. Objects are part of a hierarchy (parents) and
# properties "trickle down" differently dending on their type:
# - "relative" properties (volume, pitch, lfo, etc): final props adds from all inherited from parents
# - "absolute" properties (bus, positioning, etc): may overwrite parent's setting, so only latest matters
# - "behavior" properties (loops, delays, etc): only are used when event chain passes over those objects
#   (not an official classification,)
#
# Since "relative" properties are applied even if an event chain doesn't use reference parents, this basically
# means they are calculated from the lowest audible object (aksound/musictrack) by adding all of their parents,
# while using latest "absolute" properties found in the hierarchy. "behavior" properties are special in that
# only apply directly to each object (doesn't make sense to inherit a loop flag, since meaning is object-dependant).
#
# For example with a "family" of aksound >> switch >> actor-mixer, and event > actionplay > aksound,
# the aksound inherits properties from both ancestors (even if they don't participate in the event),
# but not a "delay" in the switch (would only affect when doing event > actionplay > switch > aksound).
# This way so one can make hierarchies and change multiple children's properties at once, even if
# parents aren't used.
#
# If some part of the family has properties that change via statechunk/rtpc, and are active, they are
# taken into account when calculating object's properties. Each only allows changing some types of
# properties though.
#
# Apart from their inheritance, "audible" objects 'pass through' their assigned "bus" (an "absolute" prop)
# Buses in turn have properties (also inherit) that then are applied over the object. These props are
# separate so you can route an object through buses with distinct effects and config. Buses can't have
# "behavior" properties (to create a delayed signal would need to use "effects").
#
# Example:
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
# Also buses are only used in "audible" objects, while parent's buses are just to be inherited
# and don't pass properties to regular objects:
#   ranseq > aksound          ranseq > aksound
#   > bus1   > ---            > bus1   > bus2
# In the first case, aksound uses bus1's props, but in the second bus1 is ignored completely
# (if bus1 has -96db, aksound will be silent in the first case, not in the second).
#
# Generally bus volumes aren't too important since final volume can be autonormalized, but in
# rare cases buses are used to fix certain .wem volumes and may contain useful statechunks
# (seen in Astral Chain wems with  "low" "mid" buses + silence states). If init.bnk is loaded
# those are applied.
#
# While the above is the basic usage of buses, they actually come in two forms:
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

_DEBUG_SIMPLER_PROPS = False # calculate like old wwiser versions (enables some of those flags)

class PropertyCalculator(object):
    def __init__(self, ws, bnode, txtp):
        self._ws = ws
        self._bnode = bnode
        self._txtp = txtp
        self._config = hnode_misc.NodeConfig()

        self._bbus = None
        self._audible = bnode.name in _HIRC_AUDIBLE
        self._is_base = None #process flag
        self._include_bus = False #process flag

    def get_properties(self):
        if _DEBUG_SIMPLER_PROPS:
            self._audible = True

        # get output bus, if possible
        self._find_bus()

        # read props from current objects and its parents
        # (base node gets behavior props, and relative only if it's audible)
        self._calculate(self._bnode)

        # read props from bus and its parents
        # those work basically the same (has parents, props/rtpcs/statechunks)
        # will also register rtpcs and statechunk combos while reading props (may be repeated)
        # (buses can't apply certain props like delays, but shouldn't be possible anyway)
        if self._include_bus:
            self._calculate(self._bbus)

        # props are clamped in Wwise to certain min/max
        self._clamp()

        return self._config

    # -------------------------------------------------------------------------

    def _find_bus(self):
        if _DEBUG_SIMPLER_PROPS:
            return
        # only audible nodes use buses
        if not self._audible:
            return
        # buses are inherited or overwritten, find first one (absolute prop)
        self._bbus = self._get_bus(self._bnode)

        # if buses aren't loaded shouldn't apply buses' properties (like busvolume)
        self._include_bus = self._bbus is not None

    def _get_bus(self, bnode):
        if not bnode:
            return None
        if bnode.bbus:
            return bnode.bbus
        return self._get_bus(bnode.bparent)


    def _clamp(self):
        cfg = self._config

        # simulate Wwise's clamps, useless but might as well
        cfg.loop = self._clamp_prop(cfg.loop, *_CLAMP_LOOPS)
        cfg.gain = self._clamp_prop(cfg.gain, *_CLAMP_VOLUME)
        cfg.delay = self._clamp_prop(cfg.delay, *_CLAMP_DELAY)


    def _clamp_prop(self, prop, min, max):
        if prop is None:
            return prop
        if prop < min:
            return min
        if prop > max:
            return max
        return prop

    # -------------------------------------------------------------------------

    # apply all properties for a node
    def _calculate(self, bnode):
        if not bnode:  #no parent
            return

        # base node applies extra props that aren't inherited
        self._is_base = self._bnode == bnode

        self._apply_props(bnode)

        self._apply_statechunks(bnode)
        self._apply_rtpclist(bnode)

        # repeat with parent nodes to simulate prop inheritance (non-playable nodes don't inherit directly)
        if self._audible and not _DEBUG_SIMPLER_PROPS:
            self._calculate(bnode.bparent)

    # -------------------------------------------------------------------------

    # standard props
    def _apply_props(self, bnode):
        if not bnode.props:  #events don't have props
            return

        cfg = self._config
        props = bnode.props

        # behavior props: only on base node
        # (props from statechunks/rtpcs are included, so must add to existing values)
        if self._is_base:
            if cfg.loop is None: #statechunks can't have this though
                cfg.loop = props.loop
            cfg.delay += props.delay

        # absolute props: first found only?
        # ...

        # relative props: only add current if base node will output audio
        if self._audible:
            cfg.gain += props.volume
            cfg.gain += props.makeupgain
            # only if we output through a bus (these are separate from bus's props)
            if self._include_bus:
                cfg.gain += props.busvolume
                cfg.gain += props.outputbusvolume

    # -------------------------------------------------------------------------

    # some objects have state = props in the statechunk, and if we have set those states we want the values
    def _apply_statechunks(self, bnode):
        if not bnode.statechunk:
            return
        cfg = self._config
        ws = self._ws

        check_info = True # always?
        if check_info:
            bscis = bnode.statechunk.get_usable_states(self._include_bus)

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
            if not bsi or not bsi.bstate:
                continue

            cfg.crossfaded = True
            self._apply_props(bsi.bstate)
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
            brtpcs = bnode.rtpclist.get_usable_rtpcs(self._include_bus)

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
                if not brtpc or not brtpc.is_usable(self._include_bus):
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

        value_y = brtpc.get(value_x)

        #TODO improve (maybe rtpc should return some mini props?)
        # apply props
        cfg = self._config

        # behavior props: only on base node
        if self._is_base:
            # RTPCs can't have loops
            if brtpc.is_delay:
                cfg.delay = brtpc.accum(value_y, cfg.delay)

        # absolute props: first found only?
        # ...

        # relative props: only add current if base node will output audio
        if self._audible:
            if brtpc.is_volume:
                cfg.gain = brtpc.accum(value_y, cfg.gain)
            if brtpc.is_makeupgain:
                cfg.gain = brtpc.accum(value_y, cfg.gain)

            if self._include_bus:
                if brtpc.is_busvolume:
                    cfg.gain = brtpc.accum(value_y, cfg.gain)
                if brtpc.is_outputbusvolume:
                    cfg.gain = brtpc.accum(value_y, cfg.gain)

        self._txtp.info.gamevar(brtpc.nid, value_x)
