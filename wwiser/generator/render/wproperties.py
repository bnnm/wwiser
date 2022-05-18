from . import bnode_misc

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
# there are "VoiceVolume", "MakeUpGain", "OutputBusVolume", "BusVolume", etc) but ultimately
# are added the final value.


# we only want 
_HIRC_AUDIBLE = {
    'CAkSound',
    'CAkMusicTrack'
}


class PropertyCalculator(object):
    def __init__(self):
        self._gvparams = None
        self._scparams = None
        self._read_bus = False

    def get_properties(self, bnode):
        if True:
            return self._calculate_simple(bnode)

        # calculate certain values depending on class
        hircname = bnode.node.get_name()

        # process flags (see _calculate)
        self._read_relative = hircname in _HIRC_AUDIBLE
        self._read_absolute = True #read absolute props until first found
        self._read_behavior = True #read behavior props only once

        # final calculated props
        self._props = bnode_misc.NodeConfig()

        # read props from hierarchy
        self._calculate(bnode)

        # calculate buses' values
        if self._read_bus:
            pass


    # older wwiser props
    def _calculate_simple(self, bnode):
        config = bnode_misc.NodeConfig()

        if not bnode.props:
            return config
        props = bnode.props

        config.loop = props.loop

        config.volume = props.volume
        config.makeupgain = props.makeupgain
        config.pitch = props.pitch
        config.delay = props.delay
        config.idelay = 0 #props.idelay

        #print("%s: props: " % (hircname))
        return config

    def _calculate(self, bnode):
        if not bnode.props: # should exist even if empty
            return

        # read relative props only if initial HIRC is at the bottom
        if self._read_relative:
            self._calc_relative(self._props, bnode.props)
            pass

        # read absolute props until first found, once ly
        if self._read_absolute:
            self._calc_relative(self._props, bnode.props)
            pass

        # read behavior props on initial object
        if self._read_behavior:
            pass

        # keep going in the hierarchy if possible
        if bnode.bparent:
            self._calculate(bnode.bparent)
            return
    
    def _calc_relative(self, p, bp):
        #p.volume += bp.voice_volume
        #p.volume += bp.makeupgain
        #p.playbackspeed *= bp.playbackspeed #similar to pitch but for music hierarchy, multiplicative
        pass

    def _calc_absolute(self, p, bp):
        #TODO detect if some 
        #self._read_absolute = False
        self._read_absolute = False

    def _calc_behavior(self, p, bp):
        #TODO loop etc
        self._read_behavior = False
