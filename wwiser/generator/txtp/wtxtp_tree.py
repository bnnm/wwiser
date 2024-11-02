from . import hnode_envelope

_DEBUG_PRINT_IGNORABLE = False

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

_VOLUME_DB_MAX = 200.0 # 96.3 #wwise editor typical range is -96.0 to +12 but allowed editable max is +-200

# Represents a TXTP tree node, that can be a "sound" (leaf file) or a "group" (includes files or groups).
# The rough tree is created by the renderer, then simplified progressively to make a cleaner .txtp file,
# transforming from Wwise concepts to TXTP commands.
# (since Wwise object's meaning depends on modes and stuff, it's easier to make a crude tree first that
# is mostly fixed, then tweak to get final tree, that may change as TXTP features are added)

class TxtpNode(object):
    def __init__(self, parent, config, sound=None):
        self.parent = parent
        self.config = config #NodeConfig
        self.sound = sound #NodeSound

        self.type = TYPE_GROUP_ROOT
        if sound:
            self.type = TYPE_SOUND_LEAF
        self.children = []

        # calculated config
        self.pad_begin = None
        self.trim_begin = None
        self.body_time = None
        self.trim_end = None
        self.pad_end = None

        # copy value as may need to simplify tree config (ex. multiple objects can set infinite loop)
        self.volume = config.gain
        self.loop = config.loop
        self.delay = config.delay

        self.crossfaded = config.crossfaded
        self.silenced = config.silenced
        self.silenced_default = config.silenced_default

        self.envelopelist = None
        if sound:
            el = hnode_envelope.NodeEnvelopeList(sound)
            if not el.empty:
                self.envelopelist = el

        # allowed to separate "loop not set" and "loop set but not looping"
        #if self.loop == 1:
        #    self.loop = None
        self.loop_anchor = False #flag to force anchors in sound
        self.loop_end = False #flag to force loop end anchors
        self.loop_killed = False #flag to show which nodes had loop killed due to trapping

        # clip loop meaning is a bit different and handled automatically
        if sound and sound.clip:
            self.loop = None

        # seen in Ghostwire: Tokyo amb_beds_daidara_Play, messes up vgmstream's calcs
        # (maybe should consider anything bigger than N an infinite loop)
        if self.loop and self.loop >= 32767:
            self.loop = 0

        self.fake_entry = False
        self.force_selectable = False


    def clamp_volume(self):
        if not self.volume:
            return
        if self.volume > _VOLUME_DB_MAX:
            self.volume = _VOLUME_DB_MAX
        elif self.volume < -_VOLUME_DB_MAX:
            self.volume = -_VOLUME_DB_MAX

    def insert_base(self, tnode):
        self.children.insert(0, tnode)

    def append(self, tnode): #TODO remove?
        self.children.append(tnode)

    def single(self):
        self.type = TYPE_GROUP_SINGLE
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

    def is_group_random(self):
        return self.is_group_random_step() or self.is_group_random_continuous()

    def is_group_random_step(self):
        return self.type in TYPE_GROUP_RANDOM_STEP

    def is_group_random_continuous(self):
        return self.type in TYPE_GROUP_RANDOM_CONTINUOUS

    #--------------------------------------------------------------------------

    def loops(self):
        return self.loop is not None and self.loop != 1

    def loops_inf(self):
        return self.loop is not None and self.loop == 0

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

        if (self.delay or self.volume) and not simpler:
            return False

        #makeupgain, pitch: ignored

        if self.trim_begin or self.trim_end or self.pad_begin or self.pad_end or self.body_time:
            return False

        if _DEBUG_PRINT_IGNORABLE:
            return False

        return True
