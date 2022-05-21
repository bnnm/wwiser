import logging, math, copy

from . import wnode_envelope
from . import wtxtp_tree


# Takes the TXTP pre-built tree and readjusts it to create a final usable tree.
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

class TxtpSimplifier(object):
    def __init__(self, printer, txtp, tree):
        self._printer = printer
        self._tree = tree
        self._txtpcache = txtp.txtpcache

        # used during process and in printer
        self.volume_master = self._txtpcache.volume_master #copy since may need to modify
        self.volume_master_auto = self._txtpcache.volume_master_auto

        # flags
        self._sound_count = 0
        self._transition_count = 0
        self._loop_groups = 0
        self._loop_sounds = 0

    # simplifies tree to simulate some Wwise features with TXTP
    def modify(self):

        #todo join some of these to minimize loops
        self._clean_tree(self._tree)
        self._set_self_loops(self._tree)
        self._set_props(self._tree)
        self._set_times(self._tree)
        self._reorder_wem(self._tree)
        self._find_loops(self._tree)
        self._set_extra(self._tree)
        self._set_volume(self._tree)


    def has_sounds(self):
        return self._sound_count > 0

    def has_noloops(self):
        return self._loop_groups == 0 and self._loop_sounds == 0

    def has_multiloops(self):
        return self._printer.has_multiloops

    def set_multiloops(self):
        self._printer.has_multiloops = True

    def set_self_loops(self):
        self._printer.has_self_loops = True

    #--------------------------------------------------------------------------

    # get first non-ignorable children
    def _get_first_child(self, node):
        if not node.ignorable():
            return node

        # logically this will stop in a sound (leaf) node or a node with N children,
        # while skipping nodes with 1 children that have no config
        for subnode in node.children:
            child = self._get_first_child(subnode)
            if child:
                return child

        return None

    #--------------------------------------------------------------------------

    # removes and simplifies nodes that aren't directly usable
    def _clean_tree(self, node):

        # iter over copy, since we may need to drop children
        for subnode in list(node.children):
            self._clean_tree(subnode)

        # kill nodes *after* iterating (bottom to top)


        # kill sound nodes that don't actually play anything, like rumble helpers (seen in AC2, MK Home Circuit)
        if node.is_sound() and node.sound.source and node.sound.source.plugin_ignorable:
            self._kill_node(node)
            return

        # kill group nodes that don't have children since they mess up some calcs
        if node.is_group() and node.parent:
            is_empty = len(node.children) == 0

            # kill segments that don't play (would generate empty silence),
            # seen in Doom Eternal (no duration) and mass effect 2 (duration but no exit)
            is_nosound = node.config.duration == 0 or node.config.exit == 0

            if is_empty or is_nosound:
                self._kill_node(node)

        # find random with all options the same (ex. No Straight Roads)
        # TODO: not working properly, should detect times and limit cases (may misdetect loops with the
        #  same .wem and different config), besides NSR doesn't work properly anyway
        #if self._has_random_repeats(node):
        #    subnode = node.children[0] #use first only
        #    node.children = [subnode]

        # set externals flag
        if node.is_sound() and node.sound.source and node.sound.source.plugin_external:
            self._printer.has_externals = True
            if node.sound.source.tid not in self._printer.externals:
                self._printer.externals.append(node.sound.source.tid)

        return

    def _kill_node(self, node):
        node.parent.children.remove(node)

    #def _has_random_repeats(self, node):
    #    if node.is_group_steps() or len(node.children) <= 1:
    #        return False
    #
    #    prev_id = None
    #    for subnode in node.children:
    #        id = self._tree_get_id(subnode)
    #        if not id:
    #            return False
    #        if prev_id is None:
    #            prev_id = id
    #        elif prev_id != id:
    #            return False
    #
    #    return True
    
    # parent's infinite loops can be removed in favor of children (since wwise loops innermost object)
    # to make txtp loop calcs a bit simpler, ex.
    # - S2 (l=0) > N1 (l=0) > ..
    # - S2 (l=0) > N1       > ..
    #            \ N1 (l=0) > ..
    # - S2 (l=0) > S2       > N1       > ..
    #                       \ N1 (l=0) > ..
    # - L2 (l=0) > N1 (l=0)
    #            \ N1 (l=0)
    def _has_iloops(self, node):
        if node.loop == 0:
            return True

        for subnode in node.children:
            if self._has_iloops(subnode):
                return True
        return False

    def _tree_get_id(self, node):
        if node.is_sound():
            if not node.sound.source:
                return None # handle plugins/silences?
            return node.sound.source.tid

        # may handle only simple groups
        if len(node.children) != 1:
            return None
        return self._tree_get_id(node.children[0])

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


        # self loop: make a clone branch (new loop), then mark the original:
        # - subnode (original): 0..entry (no loop)
        # - new_subnode (clone): entry..exit (loops)
        node.sequence_continuous()
        new_subnode = self._make_copy(node, subnode)

        subnode.self_loop = True #mark transition node
        subnode.loop = None  #0..entry
        new_subnode.loop = node.loop #mark loop node
        node.loop = None

        return True

    def _make_copy(self, new_parent, node):
        # semi-shallow copy (since some nodes have parser nodes that shouldn't be copied)

        #todo maybe implement __copy__
        new_config = copy.copy(node.config)
        new_sound = copy.copy(node.sound)
        new_transition = copy.copy(node.transition)

        #new_node = copy.copy(node) #don't clone to avoid props? (recheck)
        new_node = wtxtp_tree.TxtpNode(new_parent, sound=new_sound, config=new_config)
        new_node.type = node.type
        new_node.transition = new_transition
        # volumes can be adjusted via RTPCs after constructor
        new_node.volume = node.volume

        for envelope in node.envelopes:
            new_envelope = copy.copy(envelope)
            new_node.envelopes.append(new_envelope)

        new_parent.append(new_node)

        for subnode in node.children:
            self._make_copy(new_node, subnode)

        return new_node

    #--------------------------------------------------------------------------

    # simplify props by moving them out from single groups to child, to minimize total groups
    def _set_props(self, node):
        # do 2 passes because sometimes when moving props down it stops when same prop exists right below,
        # but after all subnodes have been processes (and props were moved down) prop can be moved again
        #todo improve (ex. Detroit  129941368 + (C05_Music_State=C05_OnNest))
        self._set_props_move(node)
        self._set_props_move(node)

        self._set_props_config(node)

    def _set_props_move(self, node):

        if node.is_group():
            is_group_single = len(node.children) == 1
            if is_group_single:
                self._move_group_props(node)

        for subnode in node.children:
            self._set_props_move(subnode)

        return

    def _move_group_props(self, node):
        # for single groups only

        # simplify any type (done here rather than on clean tree after self-loops)
        node.single()
        subnode = node.children[0]

        # move loop (not to sounds since loop is applied over finished track)
        #todo maybe can apply on some sounds (ex. S1 l=0 > L2 --- = S1 --- > L2 l=0)
        if subnode.is_group():
            is_noloop_subnode = subnode.loop is None or subnode.loop == 1
            is_bothloop = node.loop == 0 and subnode.loop == 0
            if is_noloop_subnode or is_bothloop:
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


        # move various props closer to source = better (less txtp groups)

        if not subnode.volume:
            subnode.volume = node.volume
            node.volume = None
        elif node.volume and subnode.volume and subnode.is_group_single():
            # fuse volumes to make less groups sometimes
            subnode.volume += node.volume
            node.volume = None

        if not subnode.crossfaded:
            subnode.crossfaded = node.crossfaded
            node.crossfaded = None

        if not subnode.silenced:
            subnode.silenced = node.silenced
            node.silenced = None

        if not subnode.makeupgain:
            subnode.makeupgain = node.makeupgain
            node.makeupgain = None

        if not subnode.pitch:
            subnode.pitch = node.pitch
            node.pitch = None

    def _set_props_config(self, node):
        for subnode in node.children:
            self._set_props_config(subnode)

        # whole group config
        if node.is_group():
            self._apply_group(node)

        # info
        if node.loop == 0:
            if node.is_group():
                self._loop_groups += 1
            elif node.is_sound() and not node.sound.clip: #clips can't loop forever, flag just means intra-loop
                self._loop_sounds += 1

        return

    #--------------------------------------------------------------------------

    # applies clip and transition times to nodes
    def _set_times(self, node):
        # find leaf clips and set duration
        if node.is_sound():
            if not node.sound.silent:
                self._sound_count += 1

            # convert musictrack's clip values to TXTP flags
            if node.sound.clip:
                self._apply_clip(node)
            else:
                self._apply_sfx(node)
            self._apply_automations(node)

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

    #--------------------------------------------------------------------------

    # in layered groups .wem is ordered by segment/track ids but final wem ID can move around,
    # reorder to make modding .txtp a bit easier. ex:
    # S2 > L2 > 123.wem
    #    |    > 321.wem
    #    \ L2 > 321.wem  !! (reorder to match the above)
    #         > 123.wem
    def _reorder_wem(self, node):

        for subnode in node.children:
            self._reorder_wem(subnode)

        # must only reorder layers
        # (check *after* subnode loops since this goes bottom to top)
        if not node.is_group_layers():
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

    # handle some complex loop cases
    # (assumes groups have been simplifies when no children are present)
    def _find_loops(self, node):
        if  self.has_noloops():
            return

        self._find_loops_internal(node)

    def _find_loops_internal(self, node):

        for subnode in node.children:
            self._find_loops(subnode)

        #try bottom-to-top

        # multiloops: layered groups with children that loop independently not in sync.
        # Wwise internally sets "playlists" with loops that are more like "repeats" (item ends > play item again).
        # If one layer has 2 playlists that loop, items may have different loop end times = multiloop.
        # * find if layer has multiple children and at least 1 infinite loops (vgmstream can't replicate ATM)
        # * one layer not looping while other does it's considered multiloop
        if node.is_group_layers() and not self.has_multiloops():
            for subnode in node.children:
                if self._has_iloops(subnode):
                    self.set_multiloops()
                    break

        # looping steps behave like continuous, since they get "trapped" repeating at this level (ex. Nier Automata)
        if node.loop == 0:
            if node.is_group_random_step():
                node.random_continuous()
            if node.is_group_sequence_step():
                node.sequence_continuous()

        # normal (or looping) continuous with all looping children can be treated as steps (ex. Nier Automata)
        if node.is_group_random_continuous(): #looping sequences are handled below
            iloops = 0
            for subnode in node.children:
                if self._has_iloops(subnode):
                    iloops += 1

            if iloops == len(node.children): #N iloops = children are meant to be shuffled songs
                node.random_step()
                node.loop = None # plus removes on looping on higher level to simplify behavior


        # tweak sequences
        if node.is_group_continuous():
            i = 0
            loop_ends = 0
            for subnode in node.children:
                child = self._get_first_child(subnode) #may include subnode
                i += 1

                if not child:
                    continue

                # loop resequences: sometimes a sequence mixes simple sounds with groups, that can be simplified (ex. Mario Rabbids)
                # * S2 > sound1, N1 (> sound2) == S2 > sound1, sound2
                if child.loop == 0 and child.is_group_single() and child.ignorable(skiploop=True):
                    subchild = self._get_first_child(child.children[0])
                    if subchild and subchild.loop is None:
                        subchild.loop = child.loop
                        if subchild.is_sound():
                            subchild.loop_anchor = True
                        child.loop = None
                        child = subchild

                # loop traps: when N segment items set loop first one "traps" the playlist and repeats forever, never reaching others (ex. Magatsu Wahrheit)
                # * find if segment has multiple children and loops before last children (add mark)
                if child.loop == 0:
                    if (i < len(node.children) or loop_ends > 0):
                        loop_ends += 1 #last segment is only marked if there are other segments with loop end first
                        child.loop_end = True
                    # todo maybe only if node is first usable node
                    node.loop = None #remove parent loop to simulate trapping
                    node.loop_killed = True

        return

    #--------------------------------------------------------------------------

    # extra stuff
    def _set_extra(self, node):

        # simplify first node
        basenode = self._get_first_child(node)
        if not basenode:
            return

        self._set_initial_delay(basenode)
        self._set_selectable(basenode)
        return

    def _set_initial_delay(self, node):
        # Sometimes games have events where "play" and similar objects starts delayed.
        # Not very useful and sometimes the same event without delay exists, so it's removed by default.

        if self._txtpcache.write_delays:
            return
        # only with first sfx/group, not clips (don't have delay and padding has other meaning)
        if node.is_sound() and node.sound and node.sound.clip:
            return
        node.pad_begin = 0
        node.idelay = None
        node.delay = None


    def _set_selectable(self, node):
        if not node.is_group():
            return

        count = len(node.children)
        if len(node.children) <= 1:
            return

        # set total layers/segment/randoms in the main/upper group (can be used to generate 1 .txtp per type)
        # depending on flags (may set only one or all)
        # - flag to make random groups + group is random
        random_all = self._txtpcache.random_all and node.is_group_steps()
        # - flag to make multiloops only + group isn't regular random
        random_multi = self._txtpcache.random_multi and self.has_multiloops()
        # - flag to make others
        random_force = self._txtpcache.random_force and not node.is_group_steps()

        if random_all or random_multi or random_force:
            self._printer.selectable_count = count
            node.force_selectable = True
            # set flags taking into account priority (r > m > f)
            if   random_all:
                self._printer.is_random_select = True
            elif random_multi:
                self._printer.is_multi_select = True
            elif random_force:
                self._printer.is_force_select = True

        return

    #--------------------------------------------------------------------------

    # Simplify volume stuff
    #
    # Volumes in Wwise are also a mix of buses, ActorMixers, state-set volumes and other things,
    # but usually (hopefully) volumes set on object level make the .txtp sound fine in most cases.
    #
    # However some games set low volume in base objects (ex. SFZ -14dB), since output bus volumes alter
    # this, and Wwise can normalize on realtime, plus may be used in only a few tracks as normalization
    # (ex. Dirt Rally 4, Halo Wars menus), so we need keep it. To handle this, "master volume" can be set
    # manually and it's used to alter this base volume.
    #
    # Decreasing master volume is applied to wems (lowers chances of clipping due to vgmstream's pcm16)
    # While increasing volume is applied to outmost group ()
    def _set_volume(self, node):

        self._set_volume_auto(node)

        if not self.volume_master or self.volume_master == 0:
            # no actual volume
            return

        if self.volume_master < 0:
            # negative volumes are applied per source
            self._set_volume_negative(node)
            self.volume_master = 0 #always consumed
        else:
            # positive volumes are applied in the first group that has volumes, or sound leafs otherwise
            self._set_volume_positive(node)
            # consumed manually
            return

    # Autocalculate master volume
    #
    # Tries to find a volume that would increase or lower towards 0db at once.
    # Because groups and sounds can mix high/low volumes, tries to detect final output dB from
    # all groups/nodes (from lower to higher).
    # Should be used at the end when most volumes are simplified.
    #
    # L2 a (0) > b.wem (+4)
    #          \ c.wem (-1)
    # steps:
    # - b:+4 vs c:-1 = bc:+4 (selects highest output)
    # - a:+0 + bc:+4 = +4 (adds output from children)
    # > result: auto output -4
    #
    # S2 a (-10)  > L2 b (-5)   > c.wem (+4)
    #             |             > d.wem (-1)
    #             |
    #             \ L2 e (0)    > f.wem (+1)
    #                           > S3 g (+1)  > h.wem (-2)
    #                                        | i.wem (+0)
    #                                        \ j.wem (-4)
    # steps:
    # - cd:+4
    # - b:-5 + cd:+4 = b:-1
    # - hij:+0
    # - g:+1 vs hij:+0 = g:+1
    # - f:+1 vs g:+1 = f:+1
    # - e:+0 + f:+1 = e:+1
    # - b:-1 vs e+1 = b:+0
    # - a:-10 + b:+0 = a:-10
    # > result: auto output +10

    def _set_volume_auto(self, node):
        if not self.volume_master_auto:
            return

        output = self._get_output_volume(node)
        self.volume_master = -output
        self._printer.volume_auto = -output
        return

    def _get_output_volume(self, node):
        
        output_max = None
        for subnode in node.children:
            output_sub = self._get_output_volume(subnode)
            if output_max is None or output_max < output_sub :
                output_max = output_sub

        output_self = node.volume or 0.0
        if output_max is not None:
            output_self += output_max

        return output_self

    def _set_volume_negative(self, node):
        if node.is_sound():
            node_volume = node.volume or 0.0
            node_volume += self.volume_master
            node.volume = node_volume
            node.clamp_volume()

        for subnode in node.children:
            self._set_volume_negative(subnode)

        return

    def _set_volume_positive(self, node):

        basenode = self._get_first_child(node)
        if not basenode:
            return

        # find base node and cancel its volume if possible
        if basenode.volume:
            basenode.volume += self.volume_master
            basenode.clamp_volume()
            self.volume_master = 0
            return

        # sometimes we can pass volume to lower leafs if base node didn't have volume and
        # there aren't more groups in between (better volume cancelling)
        subnodes = []
        for subnode in basenode.children:
            subbasenode = self._get_first_child(subnode)
            if not subbasenode:
                continue
            # all should be sounds
            if not subbasenode.is_sound():
                return
            subnodes.append(subbasenode)

        if subnodes:
            for subnode in subnodes:
                if not subnode.volume:
                    subnode.volume = 0
                subnode.volume += self.volume_master
                subnode.clamp_volume()
            # only if there are subnodes to pass info, otherwise it's set at the end
            self.volume_master = 0

        return

    #--------------------------------------------------------------------------

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

    def _apply_automations(self, node):
        sound = node.sound

        if not sound.automations:
            return

        # automations are relative to clip start, after applying trims/padding, that should correspond to this
        # time in seconds, unlike clip values
        base_time =  node.pad_begin / 1000.0
        version = sound.source.version

        #todo apply delays
        envelopes = wnode_envelope.build_txtp_envelopes(sound.automations, version, base_time)
        node.envelopes.extend(envelopes)


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
    # previous simplification detects self-loops and clones 2 segments, then this parts adjust segment times:
    # if entry=10, exit=100: segment1 = 0..10, segment2 = 10..100
    # since each segment may have N tracks, this applies directly to their config (body/padding/etc) values.
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
        #print("transition: entry=%s, exit=%s, before=%s" % (entry, exit, play_before))
 
        #print("**A b=%s\n pb=%s\n bt=%s\n tb=%s\n te=%s\n pe=%s" % (body, node.pad_begin, node.body_time, node.trim_begin, node.trim_end, node.pad_end))

        # hack for self-looping files: 
        if play_before and tnode.self_loop:
            # settings for 0..entry
            entry = 0
            exit = pconfig.entry
            self.set_self_loops()

        #todo fix
        #for envelope in node.envelopes:
        #    print(tnode.self_loop, play_before, entry, exit, envelope.time1, envelope.time2)
        #    pass

        if not play_before:
            # settings for entry..exit
            time = entry

            remove = time
            #print("*remove end: ", remove, node.pad_begin)
            if remove > node.pad_begin:
                remove = node.pad_begin
            #print("remove end: ", remove)
            node.pad_begin -= remove
            time -= remove

            node.trim_begin += time


        if body < exit:
            time = (exit - body)
            node.pad_end += time
        else:
            #print("*b", body, exit, time)
            time = (body - exit)
            removed = time
            if removed > node.pad_end:
                removed = node.pad_end
            node.pad_end -= removed

            time -= removed
            removed = time
            if removed > node.body_time:
                removed = node.body_time
            node.body_time -= removed
            
            # in odd cases entry may fall in the padding, so body doesn't play
            # since vgmstream needs a body ATM and this code is just a hack,
            # make some fake, tiny body (would be fixed with an overlapped layout)
            if not node.body_time:
                threshold = 5.0 / 48000.0 * 1000.0 #5 samples
                node.body_time = threshold
                #maybe should try adding to trim_end but not sure if works

            time -= removed
            removed = time
            if removed > node.pad_begin:
                removed = node.pad_begin
            node.pad_begin -= removed

            time -= removed
            if time:
                raise ValueError("non-trimmed transition %s" % (time))

        #body = node.pad_begin + node.body_time - node.trim_begin - node.trim_end + node.pad_end
        #print("**B b=%s\n pb=%s\n bt=%s\n tb=%s\n te=%s\n pe=%s" % (body, node.pad_begin, node.body_time, node.trim_begin, node.trim_end, node.pad_end))

        return
