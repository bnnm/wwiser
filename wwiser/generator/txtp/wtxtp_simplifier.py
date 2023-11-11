import logging, math, copy
from . import wtxtp_tree, wtxtp_debug, hnode_misc

_DEBUG_PRINT_TREE_PRE = False
_DEBUG_PRINT_TREE_POST = False


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
# Could be written like:
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
# Wwise objects rougly become like this:
# - event/play action: layers (can play N actions)
# - sound: simple wem
# - layer: layers
# - switch/mswitch: simple path
# - msegment > mtracks: layered tracks
#   - segment has a duration, so play time is clamped (extended or shortened)
#   - track may call an event
# - ranseq/mranseq: item groups of msegment, as a sequence or randoms (not layers)
#   - parent mranseq may have regular config/props
#   - each item may have looping config
#   - segments in playlist also needs to be clamped to entry/exit in some cases
# Simplifier is tasked to tweak those it can (ex. an event with a single action doesn't need layers)


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
        self._loop_groups = 0
        self._loop_sounds = 0

    # simplifies tree to simulate some Wwise features with TXTP
    def modify(self):
        if _DEBUG_PRINT_TREE_PRE:
            wtxtp_debug.TxtpDebug().print(self._tree, True, False)

        #TODO join some of these to minimize loops

        # SIMPLIFICATIONS:
        # To get a cleaner and simulate certain Wwise behaviors we simplify the node tree a bit:
        # - remove groups/sounds that play nothing
        # - detect if needs a "fake entry" (where a looping mranseq needs 0..entry + entry..loop)
        # - move down props, in some cases join them (as long as prop meaning doesn't change)
        # - calc time values to txtp meanings
        #   - simulate transitions by clamping some parts to entry..exit
        # - simulate playlist transitions (after removing "trap loops" would improve results a bit but also gets tripped by loop anchors)
        # - detect and try to fix "trap loops"
        # - ignore groups that don't do anything after the above simplifications
        # - other tweaks

        self._clean_tree(self._tree)
        self._make_fakeentry(self._tree)
        self._set_props(self._tree)
        self._set_times(self._tree)
        self._reorder_wem(self._tree)
        self._set_playlist(self._tree)
        self._handle_loops(self._tree)
        self._tweak_first(self._tree)
        self._set_master_volume(self._tree)

        if _DEBUG_PRINT_TREE_POST:
            wtxtp_debug.TxtpDebug().print(self._tree, False, True)


    def get_sounds_count(self):
        return self._sound_count

    def has_noloops(self):
        return self._loop_groups == 0 and self._loop_sounds == 0

    def has_multiloops(self):
        return self._printer.has_multiloops

    def set_multiloops(self):
        self._printer.has_multiloops = True

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
            if is_empty:
                self._kill_node(node)
                return

            # Kill segments that don't play (would generate empty silence), seen in Doom Eternal (no duration)
            # and mass effect 2 (duration but no exit). But only do it in playlists, to allow Detroit's
            # Play_A04_Ingame_Music (A04_Music_States=Good_Connor_Elevator_Fight_Outro)
            is_nosound = node.config.duration == 0
            is_noexit = node.config.exit == 0
            if is_nosound or is_noexit and self.is_playlist(node):
                self._kill_node(node)
                return

        # set externals flag
        if node.is_sound() and node.sound.source and node.sound.source.plugin_external:
            self._printer.has_externals = True
            if node.sound.source.tid not in self._printer.externals:
                self._printer.externals.append(node.sound.source.tid)

        return

    def _kill_node(self, node):
        node.parent.children.remove(node)
    
    def is_playlist(self, node):
        if not node:
            return False
        if node.config.rules:
            return True
        return self.is_playlist(node.parent)

    #--------------------------------------------------------------------------

    # Hack for objects that loops to itself like: mranseq (loop=0) > ... > segment
    # There are 2 transitions used: "nothing to segment start" and "segment to segment",
    # so we need a segment that plays "play_before" and loop that doesn't (since overlapped
    # transitions don't work ATM). Though in most cases this loop is very small.
    #
    # ex.    0.0 ........ 3.0 ............ 100.0 .....101.0
    #        (pre-entry)  ^ entry          ^ exit  (post-exit)
    # We have 0.0..3.0 (intro) + 3.0..100.0 (body) parts, could be simulated this like:
    # - loop point on segment level: #I 3.0 100.0
    #   - simpler but harder to handle with loop anchors (that loop whole segments)
    # - force 2 tracks: 0.. 3.0 (fake entry) + 3.0..100.0 (original)
    #   - more flexible but harder to create
    # For now we use the later since it simulates Wwise better and doesn't need to fiddle with vgmstream.
    # "fake-entry" is a clone segment that must play first (only matters when "nothing is playing"),
    # so it's put in the top-most looping group.
    def _make_fakeentry(self, node):

        # find base playlist node
        if node.config.rules: #is playlist
            self._make_fakeentry_find_segment(node, node)
            return #stop

        # can't have an inner playlist
        if node.config.duration or node.sound:
            return

        # Keep looking for playlists. Usually a .txtp only has one, but N are possible with layered playactions.
        # Playlist-within-playlist is also possible with a mtrack > playevent, but no need to apply on those
        for subnode in node.children:
            self._make_fakeentry(subnode)

        return

    # SCn                       [playlist]
    #    SC1 lpn=0              [playlist item]
    #     N1 lpn=1              [playlist item]
    #      L1                   [music segment]
    #       (duration=5000.00000, entry=2000.00000, exit=4000.00000)
    #       N1 vol=1.0          [music track]
    #        L1                 [music subtracks]
    #         snd 722952693     [music subclip]
    #          (fsd=54856.10417, fpa=1000.00000, fbt=0.00000, fet=-50856.10417)
    #   (other playlist items)
    #     (other segments)
    # We want to detect first segment and first parent that loops (within playlist), then make a new fake
    # entry segment. Between playlist and first item there may be N non-looping subitems.
    # Some cases are ignored (no loops, segment is part of random = can't quite be simulated)
    # Typical cases:
    #
    #  (simple loop)                    |  (only last 'trap' loop matters)  |  (looped with N loops)
    #  G             >  G               |  G             >  G               |  G            >  G
    #    G (L=0)          seg'          |    G (L=0)          G (L=0)       |    G (L=2)         seg'
    #      seg            G (L=0)       |      G (L=0)          seg'        |      seg           G (L=2)
    #                       seg         |        seg            G (L=0)     |                      seg
    #                                   |                         seg       |  
    #  (items in between)               |  (multi-loops)
    #  G             >  G               |  G             >  G
    #    G (L=1)          G (L=1)       |    G (L=0)          seg'
    #      G (L=0)          seg'        |      G (L=0)        G (L=2)
    #        G (L=1)        G (L=0)     |        seg            G (L=2)
    #          seg            G (L=1)   |                         seg
    #                           seg     |
    #

    # keep looking for a segment, but only first (entry segment is added to first good group of a playlist)
    def _make_fakeentry_find_segment(self, node, node_pls):

        # randoms/steps with N items that contain the first segment don't quite behave like
        # predictable loops (any segment could be the starting one)
        # layered tracks/clips is also ok
        is_valid_sequence = node.is_group_sequence_continuous() or node.is_group_sequence_step() and node.loops()
        is_valid_layer = node.is_group_layers()
        if len(node.children) != 1 and not is_valid_sequence and not is_valid_layer:
            return

        # found first segment
        if node.config.duration:
            # must have a min length of entry (not 0.0, 0.0001, etc)
            threshold = 1 / 48000.0
            if node.config.entry <= threshold:
                return
            
            valid = self._make_fakeentry_has_upper_loops(node)
            if valid:
                # fake entry is possible, where top-most node will become a container of 2:
                # - segment (clone): 0..entry (no loop)
                # - subitem (original): entry..exit (loops)

                node_parent = self._make_fakeentry_get_container(node_pls)
                if not node_parent: 
                    node_parent = node_pls
                node_parent.sequence_continuous()
                # clone needs to clone the whole subtree, since values need to be modified
                clone_seg = self._make_fakeentry_clone(node_parent, node, first=True)
                clone_seg.fake_entry = True #mark transition node (original 0..entry)
            
            return

        if node.children:
            subnode = node.children[0]
            self._make_fakeentry_find_segment(subnode, node_pls)

    # find if segment can be considered for a fake entry
    def _make_fakeentry_has_upper_loops(self, node):

        # reached top of playlist with no loops, can't make fake entry
        if node.config.rules: #is playlist
            return False

        # found looping subnode (lowest ok due to trap loops)
        if node.loops():
            return True

        return self._make_fakeentry_has_upper_loops(node.parent)

    # get best node to add the entry segment. In most cases playlist node is ok 
    # but loses some looping due trap loops:
    #  N1 > SC2 L=0 > N1 L=1  >>>  SC2 > N1 (fake)         >>>  N1 > SC3 L=0 > N1 L=1 (fake)
    #               > N1 L=0           > SC2 L=1 > N1 L=1                    > N1 L=1
    #                                            > N1 L=0                    > N1 L=0
    #   (original)                 (bad)                        (good)
    # * should put it in SC2 rather than first node or can't loop due to double group

    def _make_fakeentry_get_container(self, node):

        # can't add fakeentry here
        if node.is_group_layers() or node.config.duration or len(node.children) == 0:
            return None

        # probably only makes sense like this
        is_valid_group = (node.is_group_single() 
            or node.is_group_sequence_continuous()
            #or node.is_group_sequence_step() and node.loops() #unsure
            or node.is_group_sequence_step() and len(node.children) == 1
        )
        if not is_valid_group:
            return None

        # probably can't do anything
        if node.loops() and not node.loops_inf():
            return None

        # usable container, but only if has sub-loops in some children (otherwise defaults to playlist):
        if node.loops_inf() or len(node.children) > 1:
            for subnode in node.children:
                if self._make_fakeentry_has_lower_loops(subnode):
                    return node
            return None

        if len(node.children) > 1:
            return None
        subnode = node.children[0]
        return self._make_fakeentry_get_container(subnode)

    def _make_fakeentry_has_lower_loops(self, node):

        # reached usable bottom
        if node.is_group_layers() or node.config.duration:
            return False

        if node.loops():
            return node.loops_inf()

        for subnode in node.children:
            if self._make_fakeentry_has_lower_loops(subnode):
                return True

        return False

    def _make_fakeentry_clone(self, new_parent, node, first=False):
        # semi-shallow copy (since some nodes have parser nodes that shouldn't be copied)

        # maybe implement __copy__?
        new_config = copy.copy(node.config)
        new_sound = copy.copy(node.sound)

        #new_node = copy.copy(node) #don't clone to avoid props? (recheck)
        new_node = wtxtp_tree.TxtpNode(new_parent, sound=new_sound, config=new_config)
        new_node.type = node.type

        # when cloning nodes that have envelopes, list is automatically generated and unique,
        # but when applying entry/exit must also fix start values (done later)

        # when adding to parent, "base" fake entry goes first (intro>loop), while rest of clones
        # go in order (otherwise order becomes a bit off with layered tracks)
        if first:
            new_parent.insert_base(new_node) #insert fake entry first
        else:
            new_parent.append(new_node) #regular node otherwise

        for subnode in node.children:
            self._make_fakeentry_clone(new_node, subnode)

        return new_node

    #--------------------------------------------------------------------------

    # simplify props by moving them out from single groups to child, to minimize total groups
    def _set_props(self, node):
        # do 2 passes because sometimes when moving props down it stops when same prop exists right below,
        # but after all subnodes have been processes (and props were moved down) prop can be moved again
        #TODO improve: maybe get from parent? ex. get highest loop?
        #  (ex. Detroit  129941368 + (C05_Music_State=C05_OnNest))
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

        is_loop_node = node.loop == 0 or node.loop and node.loop > 1
        #is_loop_subnode = subnode.loop == 0 or subnode.loop and subnode.loop > 1
        is_clip_subnode = subnode.sound and subnode.sound.clip

        # move loops down to handle "trap loops" (lowest loop is what matters)
        # except on clips, that loop the whole thing
        if not is_clip_subnode:
            if is_loop_node:
                subnode.loop = node.loop
                node.loop = None

        # move delay (ok in sounds, ignore in clips --probably ok, but may mess-up transition calcs)
        if not subnode.delay and not is_loop_node and not is_clip_subnode:
            subnode.delay = node.delay
            node.delay = None


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

        if not subnode.silenced_default:
            subnode.silenced_default = node.silenced_default
            node.silenced_default = None

        if not subnode.fake_entry:
            subnode.fake_entry = node.fake_entry
            # leave fake segment flag (for easier detection)
            if not node.config.duration:
                node.fake_entry = None

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

    # applies time config, such as delays/duration/clip/transitions
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
            self._apply_envelopes(node)

        for subnode in node.children:
            self._set_times(subnode)

        # bottom to top (once the above times are correct)

        if node.config.duration:
            self._set_duration(node, node)

        return

    def _set_duration(self, node, seg_node):
        if node.config.playevent:
            return

        if node != seg_node and node.config.duration:
            logging.info("txtp: found duration inside duration") #should only happen with playevents
            return

        if node.sound and node.sound.clip:
            self._apply_duration(node, seg_node.config)

        for subnode in node.children:
            self._set_duration(subnode, seg_node)

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

    # handle some complex loop cases
    # (assumes groups have been simplifies when no children are present)
    def _handle_loops(self, node):
        if  self.has_noloops():
            return

        self._handle_loops_node(node)

    def _handle_loops_node(self, node):

        for subnode in node.children:
            self._handle_loops_node(subnode)

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
                    #TODO maybe only if node is first usable node
                    node.loop = None #remove parent loop to simulate trapping
                    node.loop_killed = True

        return

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

    #--------------------------------------------------------------------------

    # Handle common entry/exit cases. Technically could read node_playlist's rules and decide when to
    # apply pre-entry/post-exist, but almost all txtp are fine with a fake entry/exit clamp. Examples:
    # G (L=1)                          G (L=1)
    #   seg       > play all             seg'      > start-entry (fake entry)
    #                                    G (L=0)
    #                                      seg     > entry-exit
    # G (L=0)
    #   seg       > entry-exit         G (L=1)
    #   seg       > entry-exit           seg       > start..entry..exit
    #                                    seg       > entry-exit
    #                                    seg       > entry..exit..end
    #
    # (ignores start..entry/exit..end in some hard to detect cases)

    def _set_playlist(self, node):

        if node.is_sound():
            return
        if node.config.duration:
            return

        if node.config.rules:
            self._set_playlist_times(node)
            return #could try on playevents but unlikely

        for subnode in node.children:
            self._set_playlist(subnode)

        return


    def _set_playlist_times(self, node_playlist):
        segments = []

        # needs a list of segments and info to prepare some calculations
        self._set_playlist_get_segments(node_playlist, segments)

        # clamp depending on cases
        # - loops: start..entry (first segment in some cases), entry..exit (all others)
        # - no loops: start..entry..exit (first), entry..exit (mid), entry..exit..end (last)
        for index, item in enumerate(segments):
            seg_node, items, trims_node, simple_groups = item

            # group to use if clips have automations, but in some cases can be ignored
            use_group = trims_node is not None

            # decide clamp points
            if seg_node.fake_entry: #or items[0].fake_entry
                # start..entry
                clamp_begin = 0
                clamp_end = seg_node.config.entry
                use_group = False

            else:
                # start..entry, entry..exit, exit..end (these may combine)
                clamp_begin = seg_node.config.entry
                clamp_end = seg_node.config.exit

                # some games set entry=exit but that causes issues since overlaps don't work (GOW PS4)
                # for the time being ignore those and hopefully doesn't affect much (in theory could use for weird transitions)
                if clamp_begin == clamp_end: #and 
                    # for now only for "step" mranseqs
                    node_sub = node_playlist.children[0] #meh
                    if node_sub.is_group_steps():
                        continue

                # extend begin/end if segment isn't part of a loop in some cases
                if index == 0 and simple_groups:
                    clamp_begin = 0
                    use_group = False

                if index + 1 == len(segments) and simple_groups:
                    clamp_end = seg_node.config.duration

            if use_group:
                elems = [trims_node] # special "trimmable" group when trims can't be applied directly
            else:
                elems = items # in rare cases items may be groups (playevents)

            # apply on items
            for elem_node in elems:
                if elem_node.is_sound():
                    # regular segments apply trim directly to clips, that may be layered (cleaner)
                    self._apply_transition_clip(elem_node, clamp_begin, clamp_end)
                else:
                    # in some cases (like automations) must apply to a non-sound node
                    self._apply_transition_segment(elem_node, clamp_begin, clamp_end)

        return

    def _set_playlist_get_segments(self, node, segments):

        if node.config.duration: #is segment
            has_automations = False
            has_loop_anchors = False

            # get all clips (usually applies clamps on them)
            items = []
            self._set_playlist_get_clips(node, items)
            for clip in items:
                if clip.is_sound():
                    if clip.sound.automations:
                        has_automations = True
                    if clip.loop_anchor:
                        has_loop_anchors = True

            # empty segment should have been killed before
            if len(items) == 0:
                raise ValueError("No clips in segment")

            # check if things loop
            base_node = items[0].parent #in case clip has the loop flag
            if has_loop_anchors:
                simple_groups = False
            else:
                simple_groups = self._set_playlist_has_simplegroups(base_node)

            threshold = 1 / 48000.0
            has_entry = node.config.entry > threshold

            is_fake = node.fake_entry #or items[0].fake_entry

            trims_node = None
            # With automations trim must be applied over clips (envelope curves don't make sense otherwise)
            # find closest "suitable group" to apply trims, but can't be a loop node (wouldn't trim per loop
            # but once). Due to loop simplifications, loop is often in the lowest group near clip, so in some
            # cases we make a new group in between to be trimmed.
            if has_automations and has_entry and not is_fake:
                # find best usable group that can be used to apply trims
                trims_node = self._set_playlist_get_automation_group(node, None)
                if not trims_node:
                    # no non-ignorable groups, apply trim on segment
                    trims_node = node
                elif trims_node.loops():
                    # can't trim on loop groups so make a custom group in between
                    trims_node = self._set_playlist_make_trims_node(trims_node)
                else:
                    # valid non-ignorable node found to use
                    pass

            item = (node, items, trims_node, simple_groups)
            segments.append(item)
            return

        for subnode in node.children:
            self._set_playlist_get_segments(subnode, segments)

        return

    def _set_playlist_get_automation_group(self, node, best_node):
        # find lowest loop (due to trap loops) or non-ignorable node without N children

        if node.sound:
            return best_node

        if not node.ignorable():
            best_node = node

        if len(node.children) > 1:
            return best_node

        subnode = node.children[0]
        return self._set_playlist_get_automation_group(subnode, best_node)

    # From a base node (looping one) make a sub-node. Typical configs:
    # N1 L=0 >> N1 L=0        | S2 L=0 >> N1 L=0         | L2 L=0 >> N1 L=0
    #   clip      N1' (trims) |   clip      S2' (trims)  |   clip     L2' (trims)
    #               clip      |   clip        clip       |   clip       clip
    #                                           clip     |              clip
    def _set_playlist_make_trims_node(self, node):
        config = hnode_misc.NodeConfig()
        group_node = wtxtp_tree.TxtpNode(node, config)
        group_node.type = node.type
        node.single()

        # swap children
        group_node.children = node.children
        node.children = [group_node]

        # fix parents
        for subnode in group_node.children:
            subnode.parent = group_node

        return group_node

    def _set_playlist_get_clips(self, node, clips):
        if node.sound:
            clips.append(node)
            return

        # stop on "playevent" (clip that is a whole event)
        if node.config.playevent:
            clips.append(node)
            return

        for subnode in node.children:
            self._set_playlist_get_clips(subnode, clips)

        return

    # find if node has only parent that are "simple" (loops or randoms affect entry/exit decisions)
    def _set_playlist_has_simplegroups(self, low_node):
        if low_node.config.rules: #reached playlist top
            return True

        if not low_node.is_sound():
            if low_node.loops():
                return False

            if low_node.is_group_sequence_step() or low_node.is_group_random():
                return False

        return self._set_playlist_has_simplegroups(low_node.parent)

    #--------------------------------------------------------------------------

    # extra stuff for first node
    def _tweak_first(self, node):

        # simplify first node
        basenode = self._get_first_child(node)
        if not basenode:
            return

        self._set_first_delay(basenode)
        self._set_first_selectable(basenode)
        return

    def _set_first_delay(self, node):
        # Sometimes games have events where "play" and similar objects starts delayed.
        # Not very useful and sometimes the same event without delay exists, so it's removed by default.

        if self._txtpcache.write_delays:
            return
        # only with first sfx/group, not clips (don't have delay and padding has other meaning)
        if node.is_sound() and node.sound and node.sound.clip:
            return
        node.pad_begin = 0
        node.delay = None


    def _set_first_selectable(self, node):
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
    def _set_master_volume(self, node):

        if self.volume_master_auto:
            self._set_master_volume_auto(node)
            #return #may mix master volume and regular volume

        if not self.volume_master or self.volume_master == 0:
            # no actual volume
            return

        # to improve mixing and minimize clipping (due to vgmstream's PCM16):
        # - negative volumes are applied per source
        # - positive volumes are applied in the first group that has volumes, or sound leafs otherwise
        if self.volume_master < 0: #is bottom
            self._apply_master_volume_bottom(node)
            self.volume_master = 0 #always consumed
        else:
            self._apply_master_volume_top(node)
            # manually consumed in method
            return

    def _apply_master_volume_bottom(self, node):
        if node.is_sound():
            node_volume = node.volume or 0.0
            node_volume += self.volume_master
            node.volume = node_volume
            node.clamp_volume()

        for subnode in node.children:
            self._apply_master_volume_bottom(subnode)

        return

    def _apply_master_volume_top(self, node):
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

    # Autocalculate master volume
    #
    # Tries to find a volume that would increase or lower towards 0db at once.
    # Because groups and sounds can mix high/low volumes, tries to detect final output dB from
    # all groups/nodes (from lower to higher).
    # Should be used at the end when most volumes are simplified.

    def _set_master_volume_auto(self, node):
        if not self.volume_master_auto:
            return

        output = self._get_output_volume(node)
        auto_volume = -output
        self._printer.volume_auto = auto_volume

        self._apply_auto_volume(node, auto_volume)
        return

    # Max output calculations work like this:
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
    # steps (bottom to top):
    #     * cd:+4 (+4 vs -1 = +4)
    #   * b:-5 + cd:+4 = b:-1
    #       * hij:+0 (-2 vs +0 vs -4 = +0)
    #     * g:+1 + hij:+0 = g:+1
    #     * f:+1 vs g:+1 = f:+1
    #   * e:+0 + f:+1 = e:+1
    #   * b:-1 vs e+1 = e:+1
    # * a:-10 + e:+1 = a:-9
    # > result: auto output +9

    def _get_output_volume(self, node):

        # no distinction between layered or segment since they play in the "same lane" = max volume is N
        output_max = None
        for subnode in node.children:
            output_sub = self._get_output_volume(subnode)
            if output_max is None or output_max < output_sub:
                output_max = output_sub

        output_self = node.volume or 0.0
        if output_max is not None:
            output_self += output_max

        #TODO: may need to ignore silence sources
        return output_self

    # auto-volumes can be applied near original item because we know they should reasonably cancel 
    # volumes, so if group has no volumes cancel "spills down"
    #
    # L2 a (0) > b.wem (-2)    > auto = -3
    #          | c.wem (+3)    *  bcd = +3
    #          \ d.wem (-4)    *  a + bcd = +3
    #
    # - a:+0 > spill -3
    #   - b:-5, c:-3, d=-7
    #
    # S2 a (1)                    > auto = -4
    #     L2 b (3) > d.wem (-2)   * de = -2
    #              \ e.wem (-4)   * b + de = +1
    #     L2 c (0) > f.wem (+0)   * fgh = +3
    #              | g.wem (+3)   * c + fgh = +3
    #              \ H.wem (+2)   * bc = +3
    #                             * a + bd = +4
    # - a:+1 > cancel with -1, spill -3
    #   - b:+3 > cancel with -3, no spill left
    #   - c:+0 > spill -3
    #     - f:-3, g:+0, h:-1, can't spill anymore
    #
    #   S2 a (0) > S1 b (-3) > d.wem (+4)  > auto = -1
    #            |                         * b + d = +1
    #            \ S1 c (+0) > e.wem (+0)  * b vs c = +1
    #
    # - a:+0 > spill -1 (applies to both b and c)
    #   - b:-4 > no spill left
    #   - c:0 > spill -1
    #     - e:-1 > (apply since we can't spill anymore)

    def _apply_auto_volume(self, node, auto_volume):

        # cancel volume if has non-0 volume or can't spill (no more children)
        node_volume = node.volume or 0
        if not node.children: #leaf
            # full apply
            node_volume += auto_volume
            auto_volume = 0
            node.volume = node_volume

        elif node_volume:
            # partial apply (consume as much as possible)
            # - node -3 vs auto -1 > add -1, rest +0
            # - node -3 vs auto +1 > add +1, rest +0
            # - node +3 vs auto -1 > add -1, rest +0
            # - node +3 vs auto +1 > add +1, rest +0
            # - node +1 vs auto -1 > add -1, rest +0
            # - node -1 vs auto +1 > add +1, rest +0
            #
            # - node +1 vs auto -3 > add -1, rest -2
            # - node +1 vs auto +3 > add +3, rest +0 (possible?)
            # - node -1 vs auto +3 > add +1, rest +2
            # - node -1 vs auto -3 > add -3, rest +0 (possible?)

            if abs(node_volume) >= abs(auto_volume):
                add = auto_volume
                rest = 0
            else:
                # simplify?
                if node_volume > 0 and auto_volume < 0 or node_volume < 0 and auto_volume > 0:
                    add = -node_volume
                else:
                    add = auto_volume
                rest = auto_volume - add

            node_volume += add
            auto_volume = rest
            node.volume = node_volume

        # nothing to spill
        if auto_volume == 0:
            return

        # spill on each children equally
        for subnode in node.children:
            self._apply_auto_volume(subnode, auto_volume)

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

        if node.delay:
            raise ValueError("found delay in clip (%s)" % (node.delay))

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

        if node.delay: #only seen if passed from group nodes to sfx
            node.pad_begin += node.delay
        return

    def _apply_envelopes(self, node):
        if not node.envelopelist:
            return

        # Automations have points, from N.n "from" time of M.m volume making a graph (see hnode_envelope).
        # "from" time is relative to clip start (after final result with all trimming/padding/etc):
        # - clip fpa=5.0, fbt=0.0, fet=0.0, fsd=54.8 > automation from=0.0..55.8 [fpa has no effect]
        # - clip fpa=5.0, fbt=-1.0, fet=0.0, fsd=54.8 > automation from=0.0..55.8 [fbt also has no effect here]
        # - clip fpa=5.0, fbt=-1.0, fet=-0.8, fsd=54.8 > automation from=0.0..55.0 [fet only reduces curve time]
        # - clip fpa=5.0, fbt=-1.0, fet=0.2, fsd=54.8 > automation from=0.0..56.0 [***]
        # - clip fpa=5.0, fbt=1.0, fet=0.2, fsd=54.8 > automation from=0.0..56.0
        # - clip fpa=-2.0, fbt=2.0, fet=0.2, fsd=54.8 > automation from=0.0..53.0
        # *** End seems to add 1 second for some reason (doesn't affect calcs).
        # Rarely "from" becomes a very small number (-4.75...e-07), but this seems an editor oddity rather
        # than some intended meaning, as all values are near 0.0.

        # after applying clip fpas + delays we have some padding, apply to envelopes to align
        pad_time = node.pad_begin / 1000.0
        node.envelopelist.pad(pad_time)


    def _apply_group(self, node):

        if not node.pad_begin:
            node.pad_begin = 0

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

    # Apply musicranseq transition config/times between segments (ex. 100s segment may play from 10..90s)
    def _apply_transition_clip(self, snd_node, clamp_begin, clamp_end):

        # original
        body = snd_node.pad_begin + snd_node.body_time - snd_node.trim_begin - snd_node.trim_end + snd_node.pad_end

        # apply begin
        if clamp_begin:
            time = clamp_begin
            remove = time
            if remove > snd_node.pad_begin:
                remove = snd_node.pad_begin
            snd_node.pad_begin -= remove
            time -= remove
            snd_node.trim_begin += time

        # apply end
        if body < clamp_end:
            time = (clamp_end - body)
            snd_node.pad_end += time
        elif clamp_end:
            time = (body - clamp_end)
            removed = time
            if removed > snd_node.pad_end:
                removed = snd_node.pad_end
            snd_node.pad_end -= removed

            time -= removed
            removed = time
            if removed > snd_node.body_time:
                removed = snd_node.body_time
            snd_node.body_time -= removed

            # in odd cases entry may fall in the padding, so body doesn't play
            # since vgmstream needs a body ATM and this code is just a hack,
            # make some fake, tiny body (would be fixed with an overlapped layout)
            if not snd_node.body_time:
                threshold = 5.0 / 48000.0 * 1000.0 #5 samples
                snd_node.body_time = threshold
                #maybe should try adding to trim_end but not sure if works

            time -= removed
            removed = time
            if removed > snd_node.pad_begin:
                removed = snd_node.pad_begin
            snd_node.pad_begin -= removed

            time -= removed
            if time:
                raise ValueError("non-trimmed transition %s" % (time))

        return

    # when clamping to entry/exit, normally we apply it directly to clips (cleaner). But if a clip has
    # envelopes we can't since txtp envelopes apply after trims, (can't change envelope start as curve
    # meaning would change too). Instead clamp the closest parent to remove initial audio including envelope.
    def _apply_transition_segment(self, item_node, clamp_begin, clamp_end):

        # just in case
        if item_node.trim_begin or item_node.body_time:
            raise ValueError("clamped segment with trim=%s, body=%s" % (item_node.trim_begin, item_node.body_time))

        # apply settings
        
        item_node.trim_begin = clamp_begin
        item_node.body_time = clamp_end #- clamp_begin not needed, trim eats it
