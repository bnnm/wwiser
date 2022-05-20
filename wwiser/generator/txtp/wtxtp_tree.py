#import logging, math, copy



TXTP_SPACES = 1

DEBUG_PRINT_IGNORABLE = False

TYPE_SOUND_LEAF = 'snd'
TYPE_GROUP_ROOT = '.'
TYPE_GROUP_SINGLE = 'N'
TYPE_GROUP_SEQUENCE_CONTINUOUS = 'SC'
TYPE_GROUP_SEQUENCE_STEP = 'SS'
TYPE_GROUP_RANDOM_CONTINUOUS = 'RC'
TYPE_GROUP_RANDOM_STEP = 'RS'
TYPE_GROUP_LAYER = 'L'
TYPE_GROUPS = {
    TYPE_GROUP_SINGLE,
    TYPE_GROUP_SEQUENCE_CONTINUOUS,
    TYPE_GROUP_SEQUENCE_STEP,
    TYPE_GROUP_RANDOM_CONTINUOUS,
    TYPE_GROUP_RANDOM_STEP,
    TYPE_GROUP_LAYER,
}
TYPE_GROUPS_CONTINUOUS = {
    TYPE_GROUP_SEQUENCE_CONTINUOUS,
    TYPE_GROUP_RANDOM_CONTINUOUS,
}
TYPE_GROUPS_STEPS = {
    TYPE_GROUP_SEQUENCE_STEP,
    TYPE_GROUP_RANDOM_STEP,
}
TYPE_GROUPS_LAYERS = {
    TYPE_GROUP_LAYER,
}
TYPE_SOUNDS = {
    TYPE_SOUND_LEAF,
}

VOLUME_DB_MAX = 200.0 # 96.3 #wwise editor typical range is -96.0 to +12 but allowed editable max is +-200

# Represents a TXTP tree node, that can be a "sound" (leaf file) or a "group" (includes files or groups).
# The rough tree is created by the renderer, then simplified progressively to make a cleaner .txtp file,
# transforming from Wwise concepts to TXTP commands.
# (since Wwise object's meaning depends on modes and stuff, it's easier to make a crude tree first that
# is mostly fixed, then tweak to get final tree, that may change as TXTP features are added)

class TxtpNode(object):
    def __init__(self, parent, config, sound=None):
        self.parent = parent
        self.config = config #_NodeConfig
        self.sound = sound #_NodeSound
        self.transition = None #_NodeTransition

        self.type = TYPE_GROUP_ROOT
        if sound:
            self.type = TYPE_SOUND_LEAF
        self.children = []

        # config
        self.pad_begin = None
        self.trim_begin = None
        self.body_time = None
        self.trim_end = None
        self.pad_end = None

        self.envelopes = []

        # copy value as may need to simplify tree config (ex. multiple objects can set infinite loop)
        self.volume = config.volume
        self.makeupgain = config.makeupgain
        self.pitch = config.pitch
        self.loop = config.loop
        self.delay = config.delay
        self.idelay = config.idelay

        self.crossfaded = config.crossfaded
        self.silenced = False
        self._adjust_volume()


        # allowed to separate "loop not set" and "loop set but not looping"
        #if self.loop == 1:
        #    self.loop = None
        self.loop_anchor = False #flag to force anchors in sound
        self.loop_end = False #flag to force loop end anchors
        self.loop_killed = False #flag to show which nodes had loop killed due to trapping

        # clip loop meaning is a bit different and handled automatically
        if sound and sound.clip:
            self.loop = None

        self.self_loop = False
        self.force_selectable = False

    def apply_gamevars(self, gv):
        if not gv or not gv.active:
            return None
        rtpcs = self.config.rtpcs
        if not rtpcs:
            return None

        volume = self.volume or 0.0
        if self.silenced and not volume:
            volume = 96.0

        used_gamevars = []
        for rtpc in rtpcs:
            item = gv.get_item(rtpc.id)
            if not item:
                continue

            if item.min:
                rtpc_x = rtpc.min()
            elif item.max:
                rtpc_x = rtpc.max()
            else:
                rtpc_x = item.value

            # update value based on config
            volume = rtpc.get(rtpc_x, volume)
            self.clamp_volume()
            used_gamevars.append(item)

            # unsure what happens in case of conflicting RTPCs (assumed to be added, maybe depends on exclusive/etc config)
            #break

        if used_gamevars:
            self.volume = volume
        return used_gamevars

    def _adjust_volume(self):
        if self.volume and self.volume <= -96.0:
            self.volume = None
            self.silenced = True

        if self.makeupgain and self.makeupgain <= -96.0:
            self.makeupgain = None
            self.silenced = True

        # MakeUpGain is a secondary volume value, where first you set a "HDR window" in the container bus,
        # and sounds volumes are altered depending on window and MakeUpGain (meant for temp focus on some sfxs).
        # When HRD window has default settings it seems to behave like regular volume (ex. Gunslinger Stratos).
        if self.makeupgain:
            volume = self.volume or 0.0
            self.volume = volume + self.makeupgain
            #self.makeupgain = 0 #todo leave gain for info in txtp?
            self.has_others = True
            #self.has_debug = True


    def clamp_volume(self):
        if not self.volume:
            return
        if self.volume > VOLUME_DB_MAX:
            self.volume = VOLUME_DB_MAX
        elif self.volume < -VOLUME_DB_MAX:
            self.volume = -VOLUME_DB_MAX

    def append(self, tnode):
        self.children.append(tnode)

    def single(self, transition=None):
        self.type = TYPE_GROUP_SINGLE
        if (transition): #don't overwrite just in case
            self.transition = transition
        return self

    def sequence_continuous(self):
        self.type = TYPE_GROUP_SEQUENCE_CONTINUOUS
        return self

    def sequence_step(self):
        self.type = TYPE_GROUP_SEQUENCE_STEP
        return self

    def random_continuous(self):
        self.type = TYPE_GROUP_RANDOM_CONTINUOUS
        return self

    def random_step(self):
        self.type = TYPE_GROUP_RANDOM_STEP
        return self

    def layer(self):
        self.type = TYPE_GROUP_LAYER
        return self

    #--------------------------------------------------------------------------

    def is_sound(self):
        return self.type in TYPE_SOUNDS

    def is_group(self):
        return self.type in TYPE_GROUPS

    def is_group_single(self):
        return self.type in TYPE_GROUP_SINGLE

    def is_group_steps(self):
        return self.type in TYPE_GROUPS_STEPS

    def is_group_layers(self):
        return self.type in TYPE_GROUPS_LAYERS

    def is_group_continuous(self):
        return self.type in TYPE_GROUPS_CONTINUOUS

    def is_group_sequence_step(self):
        return self.type in TYPE_GROUP_SEQUENCE_STEP

    def is_group_sequence_continuous(self):
        return self.type in TYPE_GROUP_SEQUENCE_CONTINUOUS

    def is_group_random_step(self):
        return self.type in TYPE_GROUP_RANDOM_STEP

    def is_group_random_continuous(self):
        return self.type in TYPE_GROUP_RANDOM_CONTINUOUS

    #--------------------------------------------------------------------------

    # nodes that don't contribute to final .txtp so they don't need to be written
    # also loads some values
    def ignorable(self, skiploop=False, simpler=False):
        if not skiploop: #sometimes gets in the way of calcs
            if self.loop == 0: #infinite loop
                return False

        if self.loop is not None and self.loop > 1: #finite loop
            return False

        if self.type in TYPE_SOUNDS:
            return False

        if len(self.children) > 1:
            return False

        if (self.idelay or self.delay or self.volume) and not simpler:
            return False

        #makeupgain, pitch: ignored

        if DEBUG_PRINT_IGNORABLE:
            return False

        return True
