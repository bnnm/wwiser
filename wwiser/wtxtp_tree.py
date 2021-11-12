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

TYPE_GROUPS_TYPE = {
    TYPE_GROUP_SINGLE: 'S',
    TYPE_GROUP_SEQUENCE_CONTINUOUS: 'S',
    TYPE_GROUP_SEQUENCE_STEP: 'S',
    TYPE_GROUP_RANDOM_CONTINUOUS: 'R',
    TYPE_GROUP_RANDOM_STEP: 'R',
    TYPE_GROUP_LAYER: 'L',
}
TYPE_GROUPS_INFO = {
    TYPE_GROUP_SINGLE: 'single',
    TYPE_GROUP_SEQUENCE_CONTINUOUS: 'sequence-continuous',
    TYPE_GROUP_SEQUENCE_STEP: 'sequence-step',
    TYPE_GROUP_RANDOM_CONTINUOUS: 'random-continuous',
    TYPE_GROUP_RANDOM_STEP: 'random-step',
    TYPE_GROUP_LAYER: 'layer',
}

TYPE_SOUNDS = {
    TYPE_SOUND_LEAF,
}

VOLUME_DB_MAX = 200.0 # 96.3 #wwise editor typical range is -96.0 to +12 but allowed editable max is +-200

# Represents a TXTP tree node, that can be a "sound" (leaf file) or a "group" (includes files or groups).
# The rough tree is created by the rebuilder, then simplified progressively to make a cleaner .txtp file,
# transforming from Wwise concepts to TXTP commands.
# (since Wwise object's meaning depends on modes and stuff, it's easier to make a crude tree first that
# is mostly fixed, then tweak to get final tree, that may change as TXTP features are added)

class TxtpNode(object):
    def __init__(self, parent, config, sound=None, txtpcache=None):
        self.parent = parent
        self.config = config #_NodeConfig
        self.sound = sound #_NodeSound
        self.transition = None #_NodeTransition
        self.type = TYPE_GROUP_ROOT
        self.txtpcache = txtpcache
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
        # but changing config directly is no good (Wwise objects are reused)
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

    def _adjust_volume(self):
        gv = self.txtpcache.gamevars
        if not gv.active:
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
            if not self.volume:
                self.volume = 0
            self.volume += self.makeupgain
            #self.makeupgain = 0 #todo leave gain for info in txtp?
            self.has_others = True
            self.has_debug = True

        # sometimes volumes are controlled by RPTCs. By default volume isn't touched (not realistic as Init.bnk
        # sets a default), but may manually set a RTPC value:
        # - check if any of object's RTPCs have a manual value set
        # - if so, use this value (x) to get current volume (y) according to RTPC.
        if gv.active:
            for rtpc in self.config.rtpcs:
                if gv.is_value(rtpc.id):
                    rtcp_x = gv.get_value(rtpc.id)
                    #overwrite based on config and current value (otherwise couldn't set -96db)
                    self.volume = rtpc.get(rtcp_x, self.volume)
                    #break #unsure what happens in case of conflicting RTPCs
            self.clamp_volume()

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
