import logging, math, os, copy
from . import wgamesync, wtxtp_util


DEBUG_PRINT_TREE_PRE = False
DEBUG_PRINT_TREE_POST = False
DEBUG_PRINT_IGNORABLE = False
DEBUG_PRINT_GROUP_HEADER = False
DEBUG_PRINT_DISABLE_RANDOMS = False

TYPE_SOUND_LEAF = 'snd'
TYPE_GROUP_ROOT = '.'
TYPE_GROUP_SINGLE = 'N'
TYPE_GROUP_SEQUENCE = 'S'
TYPE_GROUP_RANDOM = 'R'
TYPE_GROUP_LAYER = 'L'
TYPE_GROUPS = {
    TYPE_GROUP_SINGLE,
    TYPE_GROUP_SEQUENCE,
    TYPE_GROUP_RANDOM,
    TYPE_GROUP_LAYER,
}
TYPE_GROUPS_TYPE = {
    TYPE_GROUP_SINGLE: 'S',
    TYPE_GROUP_SEQUENCE: 'S',
    TYPE_GROUP_RANDOM: 'R',
    TYPE_GROUP_LAYER: 'L',
}
TYPE_GROUPS_INFO = {
    TYPE_GROUP_SINGLE: 'single',
    TYPE_GROUP_SEQUENCE: 'sequence',
    TYPE_GROUP_RANDOM: 'random',
    TYPE_GROUP_LAYER: 'layer',
}

TYPE_SOUNDS = {
    TYPE_SOUND_LEAF,
}

# Represents a TXTP tree node, that can be a "sound" (leaf file) or a "group" (includes files or groups).
# The rough tree is created by the rebuilder, then simplified progressively to make a cleaner .txtp file,
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
        self.ignorable = False

        #config
        self.pad_begin = None
        self.trim_begin = None
        self.body_time = None
        self.trim_end = None
        self.pad_end = None

        # copy value as may need to simplify tree config (ex. multiple objects can set infinite loop)
        # but changing config directly is no good (Wwise objects repeat)
        self.loop = config.loop
        self.delay = config.delay
        self.idelay = config.idelay
        #clip loops are handled a bit differently
        if sound and sound.clip:
            self.loop = None
        self.loop_mod = None

        # allowed to separate "loop not set" and "loop set but not looping"
        #if self.loop == 1:
        #    self.loop = None

        self.self_loop = False


    def single(self, transition=None):
        self.type = TYPE_GROUP_SINGLE
        self.transition = transition
        return self

    def sequence(self):
        self.type = TYPE_GROUP_SEQUENCE
        return self

    def random(self):
        self.type = TYPE_GROUP_RANDOM
        return self

    def layer(self):
        self.type = TYPE_GROUP_LAYER
        return self

    def append(self, tnode):
        self.children.append(tnode)

#******************************************************************************

# Takes the TXTP tree pre-build and readjusts + prints it to create a final usable .txtp
# Uses txtp "groups" to handle multi layer/sequences/etc
#
# Wwise can trim/pad/modify .wem to get a final time, but can also set segment duration and entry/exit "markers"
# (to use in musicranseqs, relative to trimmed .wem), combined for loop points. Sometimes events use rather strange
# time combos, since the editor allows fiddling with each part separatedly:
#
# A file from 0..100s, that should loop from 10..90s, could be weirdly defined like:
#  event > play > musicranseq   > musicsegment    > musictrack    > 1.wem
#                 * sequence    | * duration: 12s                   * trims: 0..8s (end part is silence)
#                 * loops 2nd   | * markers: 0s/10s
#                               \ musicsegment    > musictrack    > 1.wem
#                                 * duration: 120s                  * trims: 8..150 (after 100s just repeats)
#                                 * markers: 2s/82s [relative to segment]
#
# Could written like:
#   #sequence of 2
#     #sequence of 1
#       1.wem       #b 8.0
#     group = 1S1   #b 10.0
#     #sequence of 1
#       1.wem       #r 8.0 #b 150.0
#     group = 1S1   #r 2.0  #b 82.0
#   group = 1S2
#   loop_start_segment = 2
#
# But could be rewritten as:
#   1.wem   #b 8.0  #P 2.0              # b10.0 - b8.0 = P2.0
#   1.wem   #r 10.0 #b 90.0             # r8.0 + r8.0 = r10.0, b82.0 + r8.0
# loop_state_segment = 2
#
# A musicranseq is just a playlist defining segments (like: A, B, C), but segment play time depends
# on "transitions". Transitions are set between 2 segments (like A-to-B), and decide A's final exit
# point/time and B's entry point/time (usually exit/entry) markers, plus if audio after exit/before
# entry may play. If music loops (like A,A,B,C) is would defines both A-to-A and A-to-B (see EDITOR.md).
# So A (100s segment) may set exit at 90s into B's 10s
#
# When making TXTP, segments' final play time is calculated first, then adjusted depending on entry
# points given in transitions objects. Audio before/after entry may overlap in Wwise but currently
# it's ignored.

class TxtpPrinter(object):
    LOOP_ALL  = -1  #signals "must loop the whole thing (auto not ok)"
    LOOP_AUTO = 0  #signals "may loop last segment (auto ok)"
   #LOOP_POS  = n  #signals "must loop this exact segment and no others after"


    def __init__(self, txtp, tree, txtpcache, rebuilder):
        self._tree = tree
        self._txtp = txtp
        self._txtpcache = txtpcache
        self._rebuilder = rebuilder
        self._lines = []
        self.depth = 0
        self._ignore_next = False

        self._loop_position = None
        self._sound_count = 0
        self._transition_count = 0
        self._loop_groups = 0
        self._loop_sounds = 0
        # flags
        self._randoms = False
        self._silences = False      # may use silences to change/crossfade songs
        self._self_loops = False    #
        self._streams = False       # has regular files
        self._externals = False     # special "external sources"
        self._internals = False     # internal .wem (inside .bnk)
        self._unsupported = False   # missing audio/unsupported plugins


    def process(self):
        self._modify()
        self._write()
        return ''.join(self._lines)

    def has_sounds(self):
        return self._sound_count > 0

    def has_randoms(self):
        return self._randoms

    def has_unsupported(self):
        return self._unsupported

    def has_streams(self):
        return self._streams

    def has_externals(self):
        return self._externals

    def has_internals(self):
        return self._internals

    def has_self_loops(self):
        return self._self_loops

    def has_silences(self):
        return self._silences

    def has_multiloops(self):
        #groups and sounds loop independently
        return self._loop_groups > 0 and self._loop_sounds > 0 or self._loop_groups > 1 or self._loop_sounds > 1

    def has_noloops(self):
        return self._loop_groups == 0 and self._loop_sounds == 0

    #--------------------------------------------------------------------------

    # simplifies tree to simulate some Wwise features with TXTP
    def _modify(self):
        if DEBUG_PRINT_TREE_PRE:
            logging.info("*** tree pre:")
            self._mdepth = 0
            self._print_tree(self._tree, False)
            logging.info("")

        #todo join some of these to minimize loops
        self._clean_tree(self._tree)
        self._set_self_loops(self._tree)
        self._set_props(self._tree)
        self._set_times(self._tree)
        self._set_ignorable(self._tree)
        self._reorder_wem(self._tree)
        self._find_loops(self._tree)

        if DEBUG_PRINT_TREE_POST:
            logging.info("*** tree post:")
            self._mdepth = 0
            self._print_tree(self._tree, True)
            if self._loop_position is not None:
                logging.info(" (loop pos=%s)", self._loop_position)
            logging.info("")
        return


    def _print_tree(self, node, post):
        line1 = ''
        line2 = ''
        config1 = ''
        config2 = ''

        if post:
            if node.loop is not None:       config1 += " L=%s" % (node.loop)
            if node.loop_mod is not None:   config1 += " L=*"
            if node.ignorable:              config1 += " [i]"

            if node.body_time:  config2 += ' bt={0:.5f}'.format(node.body_time)
            if node.pad_begin:  config2 += ' pb={0:.5f}'.format(node.pad_begin)
            if node.trim_begin: config2 += ' tb={0:.5f}'.format(node.trim_begin)
            if node.trim_end:   config2 += ' te={0:.5f}'.format(node.trim_end)
            if node.pad_end:    config2 += ' pb={0:.5f}'.format(node.pad_end)

        else:
            if node.config.loop is not None: config1 += " L=%s" % (node.config.loop)
            if node.config.delay:   config1 += " D=%s" % (node.config.delay)
            if node.config.idelay:  config1 += " ID=%s" % (node.config.idelay)
            if node.transition:     config1 += " (trn)"

            if node.config.entry or node.config.exit:
                dur = '{0:.5f}'.format(node.config.duration)
                ent = '{0:.5f}'.format(node.config.entry)
                exi = '{0:.5f}'.format(node.config.exit)
                config2 += " (dur=%s, ent=%s, exi=%s)" % (dur, ent, exi)

            if node.sound and node.sound.clip:
                fsd = '{0:.5f}'.format(node.sound.fsd)
                fpa = '{0:.5f}'.format(node.sound.fpa)
                fbt = '{0:.5f}'.format(node.sound.fbt)
                fet = '{0:.5f}'.format(node.sound.fet)
                config2 += " (fsd=%s, fpa=%s, fbt=%s, fet=%s)" % (fsd, fpa, fbt, fet)

        if node.type in TYPE_SOUNDS:
            tid = None
            if node.sound.source:
                tid = node.sound.source.tid
            line1 += "%s %s" % (node.type, tid)
            line1 += config1
            line2 += config2
        else:
            line1 += "%s%i" % (node.type, len(node.children))
            line1 += config1
            line2 += config2

        logging.info("%s%s" % (' ' * self._mdepth, line1))
        if line2:
            logging.info("%s%s" % (' ' * self._mdepth, line2))


        self._mdepth += 1
        for subnode in node.children:
            self._print_tree(subnode, post)
        self._mdepth -= 1

    #--------------------------------------------------------------------------

    def _clean_tree(self, node):

        # test if children have loop infinite
        if node.loop == 0:
            if self._has_iloops(node, node):
                node.loop = None

        # if multiple children in a sequence have loop infinite, only first one will play
        # todo check subchildren in  they are sequences
        if node.type == TYPE_GROUP_SEQUENCE and len(node.children) > 1:
            loop_infs = 0
            for subnode in node.children:
                if subnode.type in TYPE_GROUPS and subnode.loop == 0:
                    loop_infs += 1
                    if loop_infs > 1:
                        subnode.loop = None

        # iter over copy, since we may need to drop child
        for subnode in list(node.children):
            self._clean_tree(subnode)

        # goes *after* cleaning children
        if node.type in TYPE_GROUPS and node.parent:
            # kill group nodes that don't have children since they mess up some calcs
            is_empty = len(node.children) == 0

            # kill segments that don't play (would generate empty silence), 
            # seen in Doom Eternal (no duration) and mass effect 2 (duration but no exit)
            is_nosound = node.config.duration == 0 or node.config.exit == 0

            if is_empty or is_nosound:
                node.parent.children.remove(node)

        # find random with all options the same (ex. No Straight Roads)
        if self._has_random_repeats(node):
            subnode = node.children[0] #use first only
            node.children = [subnode]
        return

    def _has_random_repeats(self, node):
        if node.type != TYPE_GROUP_RANDOM or len(node.children) <= 1:
            return False

        prev_id = None
        for subnode in node.children:
            id = self._tree_get_id(subnode)
            if not id:
                return False
            if prev_id is None:
                prev_id = id
            elif prev_id != id:
                return False

        return True


    # parent's infinite loops can be removed in favor of children (since wwise loops innermost object)
    # to make txtp loop calcs a bit simpler, ex.
    # - S2 (l=0) > N1 (l=0) > ..
    # - S2 (l=0) > N1       > ..
    #            \ N1 (l=0) > ..
    # - S2 (l=0) > S2       > N1       > ..
    #                       \ N1 (l=0) > ..
    # - L2 (l=0) > N1 (l=0)
    #            \ N1 (l=0)
    def _has_iloops(self, node, pnode):
        if pnode != node and node.loop == 0:
            return True

        for subnode in node.children:
            if self._has_iloops(subnode, pnode):
                return True
        return False

    def _tree_get_id(self, node):
        if node.type in TYPE_SOUNDS:
            if not node.sound.source:
                return None # handle plugins/silences?
            return node.sound.source.tid

        # may handle only simple groups
        if len(node.children) != 1:
            return None
        return self._tree_get_id(node.children[0])

    #--------------------------------------------------------------------------

    # in layered groups .wem is ordered by segment/track ids but final wem ID can move around,
    # reorder to make modding .txtp a bit easier. ex:
    # S2 > L2 > 123.wem
    #    |    > 321.wem
    #    \ L2 > 321.wem !!reorder
    #         > 123.wem
    def _reorder_wem(self, node):

        for subnode in node.children:
            self._reorder_wem(subnode)

        # *after*
        if node.type == TYPE_GROUP_SEQUENCE or len(node.children) <= 1:
            return

        # find children ID
        ids = []
        for subnode in node.children:
            id = self._tree_get_id(subnode)
            if not id: #can't reorder this branch
                return
            ids.append((id, subnode))

        # may reorder now (by id only (defaults to [N+1] on equals but can't compare nodes,
        # plus same nodes must not be ordered)
        ids.sort(key=lambda x: x[0]) 
        node.children = []
        for id, subnode in ids:
            node.children.append(subnode)
        return


    #--------------------------------------------------------------------------

    # find exact loop group and simplify some in the process
    def _find_loops(self, node):
        if self.has_multiloops() or self.has_noloops():
            return
        # single sounds (sfx) loop by txtp flags (clips use loop groups)
        if self._loop_groups == 0 and self._loop_sounds == 1:
            return

        # find first non-ignorable node
        start = self._find_start(node)
        if not start:
            return #?

        count = len(start.children)

        # start node loops: must loop the whole thing
        if start.loop == 0:
            if   count == 1 or start.type != TYPE_GROUP_SEQUENCE:
                self._loop_position = self.LOOP_AUTO
            else:
                self._loop_position = self.LOOP_ALL
            return

        # child node loops: find node (if all went correctly only one direct child must be loop)
        pos = 1
        child = None
        for subnode in start.children:
            child = self._find_loop(subnode)
            if child:
                break
            pos += 1
        if not child:
            #???
            return

        if pos == count:
            self._loop_position = self.LOOP_AUTO
        else:
            self._loop_position = pos

        #group may be ignorable now we have set loop
        if self._is_ignorable(child, ignoreloop=True):
            child.ignorable = True
        child.loop = None
        child.loop_mod = True

    def _find_start(self, node):
        if not node.ignorable:
            return node

        for subnode in node.children:
            start = self._find_start(subnode)
            if start:
                return start
        return None

    def _find_loop(self, node):
        if node.loop == 0:
            return node

        for subnode in node.children:
            loop = self._find_loop(subnode)
            if loop:
                return loop
        return None

    #--------------------------------------------------------------------------

    # Hack for objects that loops to itself like: mranseq (loop=0) > item [transitions] > segment
    # There are 2 transitions used: "nothing to segment start" and "segment to segment",
    # so we need a segment that plays "play_before" and loop that doesn't (since overlapped
    # transitions don't work ATM)
    def _set_self_loops(self, node):

        if self._make_self_loop(node):
            pass #?

        for subnode in node.children:
            self._set_self_loops(subnode)

        return

    def _make_self_loop(self, node):
        if node.loop is None or node.loop == 1: #must loop
            return False

        if len(node.children) != 1: #loops to itself
            return False

        subnode = node.children[0]
        if not subnode.transition: #next part is a transition
            return False

        if len(subnode.children) != 1: #loops to itself
            return False

        subsubnode = subnode.children[0]
        if not subsubnode.config.duration or subsubnode.config.entry == 0: #next part must be a segment
            return False

        threshold = 1 / 48000.0
        if subsubnode.config.entry <= threshold: #min len
            return False


        # self loop: make a clone branch (new loop), then mark the original, so clone goes
        # from 0..entry, and original from entry..exit
        node.type = TYPE_GROUP_SEQUENCE
        new_subnode = self._make_copy(node, subnode)

        subnode.self_loop = True #mark transition node
        new_subnode.loop = node.loop #mark loop node
        node.loop = None

        return True


    def _make_copy(self, new_parent, node):
        # semi-shallow copy (since some nodes have parser nodes that shouldn't be copied)

        # todo maybe implement __copy__
        new_config = copy.copy(node.config)
        new_sound = copy.copy(node.sound)
        new_transition = copy.copy(node.transition)

        #new_node = copy.copy(node)
        new_node = TxtpNode(new_parent, sound=new_sound, config=new_config)
        new_node.type = node.type
        new_node.transition = new_transition

        new_parent.append(new_node)

        for subnode in node.children:
            self._make_copy(new_node, subnode)

        return new_node

    #--------------------------------------------------------------------------

    def _set_times(self, node):
        # find leaf clips and set duration
        if node.type in TYPE_SOUNDS:
            if not node.sound.silent:
                self._sound_count += 1

            # convert musictrack's clip values to TXTP flags
            if node.sound.clip:
                self._apply_clip(node)
            else:
                self._apply_sfx(node)

        for subnode in node.children:
            self._set_times(subnode)

        if node.config.duration:
            self._set_duration(node, node)

        if node.transition:
            self._set_transition(node, node, None)
        return

    def _set_duration(self, node, snode):
        if node != snode and node.config.duration:
            logging.info("txtp: found duration inside duration")
            return

        if node.sound and node.sound.clip:
            self._apply_duration(node, snode.config)

        for subnode in node.children:
            self._set_duration(subnode, snode)

    def _set_transition(self, node, tnode, snode):

        if node != tnode and node.transition:
            #logging.info("txtp: transition inside transition")
            #this is possible in stuff like: switch (tnode) > mranseq (node)
            return

        is_segment = node.config.duration is not None #(node.config.exit or node.config.entry)
        if is_segment and snode:
            logging.info("txtp: double segment")
            return

        if is_segment:
            snode = node
            self._transition_count += 1

        if node.sound and node.sound.clip:
            self._apply_transition(node, tnode, snode)

        for subnode in node.children:
            self._set_transition(subnode, tnode, snode)

    # simplify props by moving them out from single groups to child, to minimize total groups
    def _set_props(self, node):

        if node.type in TYPE_GROUPS:
            is_single = len(node.children) == 1
            if is_single:
                # simplify
                if node.type == TYPE_GROUP_RANDOM or node.type == TYPE_GROUP_LAYER:
                    node.type = TYPE_GROUP_SINGLE

                subnode = node.children[0]

                # move loop (not to sounds since loop is applied over finished track)
                # todo maybe can apply on some sounds
                # ex. S1 l=0 > L2 --- = S1 --- > L2 l=0
                if subnode.type in TYPE_GROUPS:
                    is_noloop_subnode = subnode.loop is None or subnode.loop == 1
                    is_multiloop = node.loop == 0 and subnode.loop == 0 #todo not too sure?
                    if is_noloop_subnode or is_multiloop:
                        subnode.loop = node.loop
                        node.loop = None

                # move delay (ok in sounds, ignore in clips)
                is_noloop_node = node.loop is None or node.loop == 1
                is_clip_subnode = subnode.sound and subnode.sound.clip #probably ok, but may mess-up transition calcs
                if not subnode.delay and is_noloop_node and not is_clip_subnode:
                    subnode.delay = node.delay
                    node.delay = None
                if not subnode.idelay and is_noloop_node and not is_clip_subnode:
                    subnode.idelay = node.idelay
                    node.idelay = None

        for subnode in node.children:
            self._set_props(subnode)

        if node.type in TYPE_GROUPS:
            self._apply_group(node)

        return

    #--------------------------------------------------------------------------

    def _set_ignorable(self, node):
        if self._is_ignorable(node):
            node.ignorable = True

        for subnode in node.children:
            self._set_ignorable(subnode)

        return

    def _is_ignorable(self, node, ignoreloop=False):
        if not ignoreloop and node.loop == 0:
            if node.type in TYPE_GROUPS:
                self._loop_groups += 1
            elif not node.sound.clip:
                self._loop_sounds += 1
            #clips can't loop forever, flag just means intra-loop

            return False

        if DEBUG_PRINT_IGNORABLE:
            return False

        if node.type in TYPE_SOUNDS:
            return False

        if len(node.children) > 1:
            return False

        if node.loop is not None and node.loop > 1:
            return False

        if node.idelay or node.delay:
            return False

        return True


    # translates Wwise clip values to TXTP config:
    # - fsd (fSrcDuration): original base file duration, for calcs (not final time)
    # - fpa (fPlayAt): moves/pads track from start (>0=right, <0=left)
    # - fbt (fBeginTrimOffset): mods beginning (>0=trim begin, <0=add end repeat)
    # - fet (fEndTrimOffset): mods end (<0=trim end, >0=add start repeat)
    #
    # ex. with fsd=30s (#b 30.0)
    # fpa=+10 fbt=0   fet=0     > #p 10.0           (moves right = adds padding)
    # fpa=-10 fbt=*   fet=0     > -                 (moves left before beginning, but always comes with a trim)
    # fpa=0   fbt=+10 fet=0     > #r 10.0 #p 10.0   (trims beginning + moves left)
    # fpa=+10 fbt=+10 fet=0     > #r 10.0 #p 20.0   (moves right + trims beginning + moves right)
    # fpa=0   fbt=0   fet=-10   > #R 10.0           (trims end)
    # fpa=0   fbt=-10 fet=+10   > !!!               (this case adds repeats)
    # fpa=-5, fbt=-5, fet=0     > !!!               (shouldn't be possible)
    #
    # clips' "repeat" parts are N partial loops (can't loop forever, only full loops):
    #    (  << repeat/-fbt  | base/fsd   |  repeat/+fet >>  )
    #    (67|0123456789|0123456789|0123456789|12)  > bte -12s, fsd=10s, fet=+12s
    #
    # reworded for TXTP (body N times + trims: 1 base + N from negative fbt + N from positive fet)
    #   fpa=-   fbt=-40 fet=+40   > #r 20.0 #b 150.0 #R 20.0
    #       * base:         (repeat-10|repeat-30|clip+30|repeat+30|repeat+10)
    #       * mod:   trim+20(clip+10|clip+30|clip+30|clip+30|clip+10)

    def _apply_clip(self, node):
        sound = node.sound
        #config = node.config

        if node.delay or node.idelay:
            raise ValueError("found delay/idelay in clip (%s, %s)" % (node.delay, node.idelay))

        body_time = 0.0
        pad_begin = 0.0
        trim_begin = 0.0
        trim_end = 0.0
        pad_end = 0.0

        threshold = 1.0 / 48000.0

        # remove repeats that are too small to even make a sample since they tend to create big trims
        # that end up consuming a whole loop = useless (mini trims are ok, will be removed later)
        if sound.fbt < 0 and sound.fbt > -threshold:
            #sound.fpa += sound.fbt ?
            sound.fbt = 0
            if sound.fet > 0 and sound.fet < threshold:
                sound.fet = 0


        body_time = sound.fsd

        #handle begin pad (may be negative, should be cancelled by bft)
        pad_begin += sound.fpa

        # handle begin trim (>0) or begin repeat (<0)
        if sound.fbt >= 0:
            trim_begin += sound.fbt
            pad_begin += sound.fbt
        else:
            repeat = math.fabs(sound.fbt)
            trim = math.fabs(sound.fbt % sound.fsd)

            body_time += repeat + trim
            trim_begin += trim
            pad_begin -= repeat

        # handle end trim (<0) or end repeat (>0)
        if sound.fet <= 0:
            trim_end += math.fabs(sound.fet)
        else:
            repeat = sound.fet
            body_time += repeat

        # clean very small negative values that happen due to rounding, ex. South Park TFBH's
        #  3283341: fpa=-321.158447971784 + fbt=321.158447971783 = -0.000000000001
        if pad_begin < 0 and pad_begin > -threshold:
            pad_begin = 0
        if trim_begin < 0 and trim_begin > -threshold:
            trim_begin = 0

        # validations
        #if sound.fpa < 0 and -sound.fpa != sound.fbt:
        #    # possible with some delta, ex. -5166.66666666666 vs 5166.66666666667
        #    raise ValueError("negative fpa with different fbt: %s vs %s" % (sound.fpa, sound.fbt))
        if body_time < 0 or pad_begin < 0 or trim_begin < 0 or trim_end < 0:
            raise ValueError("negative TXTP clip values: b=%s, p=%s, r=%s, R=%s" % (body_time, pad_begin, trim_begin, trim_end) )
        if body_time - trim_begin - trim_end < 0:
            raise ValueError("wrong TXTP clip values")

        # clean a bit (also done by TXTP but makes simpler .txtp)
        if trim_end and trim_end <= body_time:
            body_time -= trim_end
            trim_end = 0

        node.pad_begin = pad_begin
        node.trim_begin = trim_begin
        node.body_time = body_time
        node.trim_end = trim_end
        node.pad_end = pad_end
        return

    def _apply_sfx(self, node):
        if not node.pad_begin:
            node.pad_begin = 0

        if node.idelay:
            node.pad_begin += node.idelay
        if node.delay: #only seen if passed from group nodes to sfx
            node.pad_begin += node.delay
        return

    def _apply_group(self, node):

        if not node.pad_begin:
            node.pad_begin = 0

        if node.idelay:
            node.pad_begin += node.idelay
        if node.delay:
            node.pad_begin += node.delay
        return

    # apply musicsegment's duration to converted clip values. Duration is typically max clip length,
    # but can extended beyond, though that is usually undone by musicranseqs transitions
    def _apply_duration(self, node, pconfig):
        if not pconfig or not pconfig.duration:
            return

        # maybe should only apply to clip if segment has only 1 children, otherwise just apply to
        # group (more clear), but may make easier to copypaste wems if applied to clips
 
        body_full = node.pad_begin + node.body_time - node.trim_begin - node.trim_end
        #delta = 0.00000000001 #some leeway after calcs
        # possible
        #if pconfig.duration + delta < body_full and pconfig.exit and pconfig.duration != pconfig.exit:
        #    logging.info("txtp: segment duration smaller %s than clip %s", pconfig.duration, body_full)
        if pconfig.exit and pconfig.duration < pconfig.exit :
            logging.info("txtp: segment duration smaller %s than exit %s", pconfig.duration, pconfig.exit)

        if pconfig.duration > body_full:
            node.pad_end = pconfig.duration - body_full

        # for silences
        if not node.body_time and node.pad_end:
            node.body_time = node.pad_end
            node.pad_end = 0

    # apply musicranseq transition config/times between segments (ex. 100s segment may play from 10..90s)
    # wwise allows to overlap entry/exit audio but it's not simulated ATM
    def _apply_transition(self, node, tnode, snode):
        #if not snode:
        #    logging.info("generator: empty segment?")
        #    return

        #transition = tnode.transition
        pconfig = snode.config

        body = node.pad_begin + node.body_time - node.trim_begin - node.trim_end + node.pad_end
        entry = pconfig.entry
        exit = pconfig.exit

        #since we don't simulate pre-entry, just play it if it's first segment
        play_before = self._transition_count == 1 #todo load + check transition.play_begin
        if play_before and tnode.self_loop: #hack for self-looping files
            entry = 0
            exit = pconfig.entry
            self._self_loops = True

        if not play_before:
            time = entry

            remove = time
            if remove > node.pad_begin:
                remove = node.pad_begin
            node.pad_begin -= remove
            time -= remove

            node.trim_begin += time


        if body < exit:
            time = (exit - body)

            node.pad_end += time
        else:
            time = (body - exit)

            removed = time
            if removed > node.pad_end:
                removed = node.pad_end
            node.pad_end -= removed
            time -= removed

            node.body_time -= time

        return


    #--------------------------------------------------------------------------

    # prints tree as a .txtp
    def _write(self):
        # generic nodes
        self._write_node(self._tree)
        self._lines.append('\n')

        # final commands
        if self._loop_position is not None:
            line = ''
            if self._loop_position == self.LOOP_AUTO:
                # must loop the last segment (also loops if only 1 segment)
                line += 'loop_mode = auto'
            elif self._loop_position == self.LOOP_ALL:
                # must loop the whole thing
                line += 'loop_start_segment = 1\n'
            else:
                # must loop one exact segment
                line += 'loop_start_segment = %s\n' % (self._loop_position)
                line += 'loop_end_segment = %s\n' % (self._loop_position)
            self._lines.append('%s\n' % (line))
        return


    def _write_node(self, node):
        if not node.ignorable:
            self.depth += 1

        if   node.type in TYPE_SOUNDS:
            self._write_sound(node)
        elif node.type in TYPE_GROUPS:
            self._write_group_header(node)

        pos = 0 #todo preprocess?
        for subnode in node.children:
            if DEBUG_PRINT_DISABLE_RANDOMS and pos > 0 and node.type == TYPE_GROUP_RANDOM:
                self._ignore_next_default = self._ignore_next
                self._ignore_next = True

            self._write_node(subnode)

            if DEBUG_PRINT_DISABLE_RANDOMS and pos > 0 and node.type == TYPE_GROUP_RANDOM:
                self._ignore_next = self._ignore_next_default

            pos += 1

        #TXTP groups need to go to the end
        if node.type in TYPE_GROUPS:
            self._write_group(node)

        if not node.ignorable:
            self.depth -= 1

        # set flag with final tree since randoms of a single file can be simplified
        if node.type == TYPE_GROUP_RANDOM and len(node.children) > 1:
            self._randoms = True
        if node.config.volume == -96.0:
            self._silences = True


    # make a TXTP group
    def _write_group(self, node):
        #ignore dumb nodes that don't contribute (children are output though)
        if node.ignorable:
            return

        # ex. -L2: at position N (auto), layers previous 2 files
        config = node.config
        type = TYPE_GROUPS_TYPE[node.type]
        count = len(node.children)
        ignored = self._ignore_next #or count <= 1 #allow 1 for looping full segments
        if DEBUG_PRINT_DISABLE_RANDOMS and type == TYPE_GROUP_RANDOM:
            ignored = True

        line = ''
        mods = ''
        info = ''
        if ignored:
            line += '#'

        # add base group
        line += 'group = -%s%s' % (type, count)
        if type == TYPE_GROUP_RANDOM:
            line += '>1'
            info += '  ##select >N of %i' % (count)

        # add config
        if node.loop is not None:
            if   node.loop == 0 and self.has_multiloops():
                info += ' ##loop'
            elif node.loop > 1:
                mods += ' #E #l %i.0' % (node.loop)

        mods += self._get_ms(' #p', node.pad_begin)

        # this probably depends on all previous volumes and bus volume, left for reference
        if config.volume is not None:
            volume = config.volume #todo db to %
            info += '  ##@volume %sdb' % (volume)

        # wwise seems to mix to highest
        if type == TYPE_GROUP_LAYER:
            mods += ' #@layer-e' #'e' is needed for Wwise demos

        pad = self._get_padding()
        self._lines.append('%s%s%s%s\n' % (pad, line, mods, info))


    # make a TXTP group header
    def _write_group_header(self, node):
        if not DEBUG_PRINT_GROUP_HEADER:
            return #not too useful
        if node.ignorable:
            return

        line = ''

        line += '#%s of %s' % (TYPE_GROUPS_INFO[node.type], len(node.children))
        if node.loop is not None:
            if   node.loop == 0:
                line += ' (N loops)'
            elif node.loop > 1:
                line += ' (%i loops)' % (node.loop)

        pad = self._get_padding()
        self._lines.append('%s%s\n' % (pad, line))


    # write a TXTP sound wem
    def _write_sound(self, node):
        sound = node.sound
        ignored = self._ignore_next

        line = ''
        mods = ''
        info = ''
        if ignored:
            line += '#'

        name = self._txtpcache.wemdir
        if sound.source and self._txtpcache.wemsubdir:
            name += sound.source.subdir()

        # add source
        if   sound.silent:
            name = "?.silent"

        elif sound.source.plugin_id:
            name = "?.plugin-%s" % (sound.source.plugin_id)
            if sound.source.plugin_id == "00650002":
                info += " ##silence"
            else:
                self._unsupported = True

        elif sound.source.plugin_external:
            name = "?.external-%s" % (sound.source.tid)
            self._externals = True

        elif sound.source.internal and not self._txtpcache.bnkskip:
            bankname = sound.nsrc.get_root().get_filename()
            media = self._rebuilder.get_media_index(bankname, sound.source.tid)
            extension = sound.source.extension
            if self._txtpcache.alt_exts:
                extension = sound.source.extension_alt

            if media:
                bankname, index = media
                name += "%s #s%s" % (bankname, index + 1)
                info += " ##%s.%s" % (sound.source.tid, extension)
            else:
                name = "?" + name + "%s.%s" % (sound.source.tid, extension)
                info += " ##bnk?"
                self._unsupported = True
            self._internals = True
            self._txtpcache.register_bank(bankname)

        else:
            extension = sound.source.extension
            if self._txtpcache.alt_exts:
                extension = sound.source.extension_alt

            name += "%s.%s" % (sound.source.tid, extension)
            self._streams = True


        line += name

        # add config
        if sound.clip: #CAkMusicTrack's clip
            mods += self._get_clip(sound, node)
        else: #CAkSound
            mods += self._get_sfx(sound, node)

        # this probably depends on all previous volumes and bus volume, so maybe it isn't wanted
        #if config.volume is not None:
        #    volume = config.volume #todo db to %
        #    info += '  ##@volume %sdb' % (config.volume)

        # final .wem are padded to help understand the flow (TXTP trims whitespace filenames/groups)
        pad = self._get_padding()
        self._lines.append('%s%s%s%s\n' % (pad, line, mods, info))

        #todo extra line to mimic groups
        #if node.parent and node.parent.ignorable and len(node.parent.children) == 1:
        #    self._lines.append('\n')


    def _get_sfx(self, sound, node):
        #sfx are mostly pre-modified before generation, so main config is looping
        mods = ''

        if node.loop is not None:
            # we don't go parsing whole .wems to figure out loops so always write flags
            if node.loop == 1:
                mods += ' #i'
            else:
                #uses internal loops if set, or full loops otherwise
                if not self._txtpcache.x_loops: #some games don't seem to follow this (KOF12/13)
                    mods += ' #e'
                # 0=infinite
                if node.loop > 1:
                    mods += ' #l %s.0' % (node.loop)

        mods += self._get_ms(' #p', node.pad_begin)
        #mods += self._get_ms(' #b', node.body_time)
        #mods += self._get_ms(' #r', node.trim_begin)
        #mods += self._get_ms(' #R', node.trim_end)
        #mods += self._get_ms(' #P', node.pad_end)
        return mods

    def _get_clip(self, sound, node):
        mods = ''

        # final body time goes over 1 loop (not using loop flag since it seems to depend on final trim, see examples)
        # some files slightly over duration (ex. 5000 samples) and are meant to be looped as segments, it's normal

        if sound.silent:
            pass
        elif node.body_time - node.trim_end > sound.fsd: # trim_begin not included
            mods += ' #E' #clips only do full loops
            if self._sound_count == 1:
                mods += ' #f 0.0 #d 0.0' #for single wems so fade isn't added to body time
        else:
            mods += ' #i' #just in case

        mods += self._get_ms(' #p', node.pad_begin)
        mods += self._get_ms(' #b', node.body_time)
        mods += self._get_ms(' #r', node.trim_begin)
        mods += self._get_ms(' #R', node.trim_end)
        mods += self._get_ms(' #P', node.pad_end)

        return mods

    def _get_ms(self, param, value_ms):
        if not value_ms:
            return ''
        value_sec = value_ms / 1000
        value_str = str(value_sec) #default, no 0 padding
        if 'e' in value_str:
            # has scientific notation, use format to fix/truncate (9.22e-06 > 0.0000092213114704)
            # there may be some precission loss but shouldn't matter (wwise doesn't seem to round up)
            value_str = '{0:.10f}'.format(value_sec)
            if not float(value_str): # truncated result may be 0.000000
                return ''
        #todo ignore trims that end up being 0 samples (value * second = sample)

        out = '%s %s' % (param, value_str)
        return out

    def _get_padding(self):
        return ' ' * (self.depth - 1)
