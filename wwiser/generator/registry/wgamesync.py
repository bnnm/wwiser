import logging, re
from . import wparams
from ... import wfnv


DEBUG_PRINT_TREE_BASE = False
DEBUG_PRINT_TREE_COMBOS = False
DEBUG_PRINT_TREE_MAKING = False
DEBUG_PRINT_TREE_TEXT = False
DEBUG_DEPTH_MULT = 2
DEBUG_ALLOW_DYNAMIC_PATHS = False


# GAMESYNCS' STATE/SWITCH PATHS
# Some objects depend on states/switches. When parsing a root node, by default the
# generator tries to find and save all possible paths, for example (for a complex case):
#  (event) --> (switch) --> music=bgm1 --> act=st1   = path1
#                       |              \-> act=st2   = path2
#                       |
#                       \-> music=bgm2 + section=01 --> act=* (any)  = path3
#                       |
#                       \-> music=bgm2 + section=02 --> act=st3      = path4
#
# Once the "tree" list is done (no .txtp written), it creates combos of variables that
# make each path, and generates one .txtp per path with "active" vars:
#   [music=bgm1, act=st1] >> txtp1
#   [music=bgm1, act=st2] >> txtp2
#   [music=bgm2, section=01, act=*] >> txtp3
#   [music=bgm2, section=02, act=st3] >> txtp4
#
# It's done this way to mimic Wwise, and to allow user set variables externally for certain config.
# Real gamesyncs are global or per game object (so same event + vars changes by character),
# but there is no need to simulate that, as the generator acts like a "global game object".
#
# Final order shouldn't matter as vars are set to a single value:
#   music=bgm01 -> act=st1 + music=bgm02   (music can't be 2 things at the same time)
# This is possible though:
#   music=bgm01 -> act=st1 + music=*       (last node just expects "music" to be defined/set)
# The former wouldn't reach a valid node, but it's ok to have such paths in banks (unused remnants).
#
# You can have a "music" state and "music" switch that are named the same, as long as type
# (switch/state) is different, so vars are represented by [type + name/key + value].
#
#
# Instead of saving paths, we could try to generate a combo of all possible variables too
# (like [music=bgm1 + act=st1 + section=02], even if unlikely). However some games use +30
# variables in some paths (Nier AT, Death Stranding ~23), so the amount of combos is too high.
# With "tree paths" it won't try to create useless paths like [music=bgm2, act=st1/st2],
# but it's more complex to set up.
#
# Code populates tree like:
#
#   for ...
#       paths.add(gamesync1)                # starts sub-path1
#       ... (calls to next audio object)
#           for ...
#               paths.add(gamesync2)        #   starts sub-path2
#                   ... (calls)
#               paths.done()                #   ends sub-path2
#       paths.done()                        # ends sub-path1

# PATH TYPES
#
# Switches can contain switches, so some paths get pretty complex. In Wwise (at least in the editor)
# when a var changes all switch nodes are updated, meaning the whole tree must make sense or nothing plays
# (doesn't just use current/last switch node). Basically upper nodes "gate" lower nodes.
#
# * simple switch
#   - path1: scene=s1 (track1)
#   - path2: scene=s2 (track2)
#   - path3: scene=*  (track3, special "any" value is also treated as a state value)
#   / path4: scene=s3 (no child node, so this path isn't added)
#   / path4: scene=s4 (could be a valid value elsewhere, but not found in this tree so ignored)
#  ev > action > switch: [scene]
#                         =s1  >  segment/track1
#                         =s2  >  segment/track2
#                         =s3  >  none
#                         =*   >  segment/track3
#
# * multi-value switch
#   - path1: gameplay=main_menu, scene=s1 (track1)
#   - path2: gameplay=main_menu, scene=s2 (track2)
#   - path3: gameplay=gameplay, scene=*  (track3)
#  ev > action > switch: (gameplay)   [scene]
#                         =main_menu   =s1  >  segment/track1
#                         =main_menu   =s1  >  segment/track2
#                         =gameplay    =*   >  segment/track3
#
# * nested switches
#   - path1: music=main_menu (track1)
#   - path2: music=gameplay, scene=s1 (track2)
#   - path3: music=gameplay, scene=s2 (track3)
#  ev > action > switch: (music)
#                         =main_menu  >  segment/track1
#                         =gameplay   >  switch: [scene]
#                                                 =s1  >  segment/track2
#                                                 =s2  >  segment/track3
#
# * nested switches with dead paths (same vars)
#   - path1: music=gameplay (track1)
#   / path2: music=pause                 **invalid (can't get past of first switch)
#   / path2: music=gameplay, music=pause **dead (changing from music=gameplay to music=pause closes first switch)
#  ev > action > switch: (music)
#                         =gameplay  >  switch: (music)
#                                                =gameplay  >  segment/track1
#                                                =pause     >  segment/track2 **dead
#
# * layered switches (same)
#   - path1: music=gameplay (layered track1 + track2)
#  ev > action > switch: (music)
#     \                   =gameplay  > track1
#     > action > switch: (music)
#                         =gameplay  > track2
#
# * layered switches (different)
#   - path1: music=gameplay + scene=invalid (track1)
#   - path2: music=invalid  + scene=s1 (track2)
#   / path3: music=gameplay + scene=s1 (layered track1 + track2)
#  ev > action > switch: (music)
#     \                   =gameplay  > segment/track1
#     > action > switch: [scene]
#                         =s1  > segment/track2
#
# At the moment layered combos aren't generated and only one path can be active.
# (those paths could be non-existent in game, if devs manually avoid mixing certain cases).
# Because there may be many sub-combos, all possible paths can be lots of combinations:
# - action1 only
# - ...
# - actionN only
# - action1 paths + action2 paths
# - action1 paths + action3 paths
# - action1 paths + action2 paths + action3 paths
# - ...
#
# It's also possible (but very rare) to have layered switches
#
# ? check if layered switches are possible elsewhere
# ? option to enable layered combos after non-layered (use combinations)
# ? check itertools generator instead of lists
#
# ---------------------------------------------------------

class _GamesyncNode(object):
    def __init__(self, parent, gamesyncs, txtpcache):
        self._wwnames = txtpcache.wwnames
        self.parent = parent
        self.elems = gamesyncs #a list for nodes with multiple gamesyncs at once
        self.children = []

        if txtpcache.x_prefilter_paths:
            self.params = {}
            for type, name, value in gamesyncs:
                self.params[(type, name)] = value

    def append(self, node):
        self.children.append(node)

    def __lt__(self, other):
        # sorting gamesyncs:
        # - items are names or ids adapted to be sorted (see _sortvalue)
        # - 'other' should have the same number of elems (compares between nodes of the same parent)
        # - groups are fixed, so order is as found
        # - types/groups also shouldn't vary between self/other (same parent), so only needs to check values
        # - values must be ordered but 0 (any) goes first (improves dupes in most cases)
        #   - may be useful to give weight to some items (to force "any" go last)

        # should't happen but...
        len1 = len(self.elems)
        len2 = len(other.elems)
        if len1 != len2:
            return len1 < len2

        # elems can be a list of N
        items1 = []
        items2 = []
        for i, (elem1, elem2) in enumerate(zip(self.elems, other.elems)):
            nvalue1 = self._sortvalue(elem1[1], elem1[2])
            nvalue2 = self._sortvalue(elem2[1], elem2[2])

            items1.append((i, nvalue1))
            items2.append((i, nvalue2))

        return items1 < items2

    def _sortvalue(self, g_id, v_id):
        # 0 goes first
        #if v_id == 0:
        #    weight = 0
        #    return "%s-%s" % (weight, v_id)


        # hashname or ~ to force numbers after letters
        g_name = None
        g_row = self._wwnames.get_namerow(g_id)
        if g_row and g_row.hashname:
            g_name = g_row.hashname

        v_name = None
        if v_id == 0:
            v_name = '-'
        else:
            v_row = self._wwnames.get_namerow(v_id)
            if v_row and v_row.hashname:
                v_name = v_row.hashname

        if v_name:
            weight = self._wwnames.get_weight(g_name, v_name)
            return "%s-%s" % (weight, v_name)
        else:
            return "~%s" % (v_id)

# ---------------------------------------------------------

def _get_info(txtpcache, id):
    try:
        if not txtpcache.wwnames:
            return id
    except AttributeError:
        return id

    row = txtpcache.wwnames.get_namerow(id)
    if row and row.hashname:
        #return "%s=%s" % (row.hashname, id)
        return "%s" % (row.hashname)
    else:
        return id


# stores current selected switch path
class GamesyncParams(object):

    def __init__(self, txtpcache):
        self._empty = True
        self._elems = {}
        self._txtpcache = txtpcache
        self._manual = False
        self._fnv = wfnv.Fnv()
        self._depth = 0 #info

    def is_empty(self):
        return self._empty

    def get_elems(self):
        elems = []
        for key in self._elems:
            type, name = key
            values = self._elems[key]
            for value in values:
                elems.append((type, name, value))
        return elems

    def key(self):
        return frozenset(self.get_elems())

    # internal registers
    def adds(self, gamesyncs):
        unreachables = False
        for gamesync in gamesyncs:
            unreachable = self.add(*gamesync)
            if unreachable:
                unreachables = True
        return unreachables

    def add(self, type, name, value):
        self._empty = False

        type = int(type)
        name = int(name)
        value = int(value)

        unreachable = False

        key = (type, name)
        if key not in self._elems:
            self._elems[key] = []
        else:
            # detect if another non * value exists (may always useful as other paths could exist)
            if value not in self._elems[key] and value != 0 and 0 not in self._elems[key]:
                logging.debug(" maybe unreachable: %s,%s,%s", type, name, value)
                unreachable = True

        # vars are added to a list to (possibly) detect paths that could only be reached with dynamic changes
        # - switch music=bgm1 > (switch music=bgm1)
        #                     > (switch music=bgm2) **unreachable if music is always bgm1
        # In theory this can't happen (Wwise editor can't reach bgm2) but a few games have such nodes.
        #
        # Those paths may be generated and considered unused, but it's hard to handle them.
        # For now mark them as "unreachable" so the rebuilder doesn't try to call sub-nodes (would consider them as used)
        # Probably could overwrite current 0 values and reject any non-0 value.

        if DEBUG_PRINT_TREE_MAKING:
            logging.debug("GS added: %s%s, %s, %s" % (' ' * self._depth * DEBUG_DEPTH_MULT, type, self._get_info(name), self._get_info(value)))

        self._elems[key].append(value)

        return unreachable

    # get currently set single value of gamesync
    def current(self, type, name):
        key = (type, name)

        values = self._elems.get(key)
        if not values:
            # Normally doesn't happen, but when multiple paths play at once, only one is active ATM
            # and other paths won't find their variables set (combos get too complex when mixing multi-paths)
            # ex. multiple play actions in event, or multiple switch-type tracks in a segment
            # May happen when generating certain paths too?
            if DEBUG_PRINT_TREE_TEXT:
                logging.debug("generator: expected gamesync (%s, %s) not set" % (wparams.TYPE_NAMES[type], self._get_info(name)))
            self._txtpcache.stats.multitrack += 1
            return None

        if self._manual and len(values) == 1:
            # get first and don't pop in manual params (assumes correct)
            value = values[0]
        else:
            # get "last" value, since paths are read from bottom to top means uppermost variable
            # because it could be a "*" (0), favor last non-0 (gets some extra paths in complex cases)
            # ex. bgm=* ... bgm=b001 ... bgm=b002 (favors b001 as it gets a few extra paths, ex. NierAT)
            # ex. bgm=b002 ... bgm=* (favors b002)
            value = 0
            for tmp in values:
                if tmp == 0:
                    continue
                value = tmp

            # pop values to simulate dynamic changes, though shouldn't happen nor be needed
            if DEBUG_ALLOW_DYNAMIC_PATHS:
                value = values.pop()

        if DEBUG_PRINT_TREE_TEXT:
            logging.debug("gamesync: get %s, %s, %s" % (type, self._get_info(name), self._get_info(value)))
        return value

    def add_gsparam(self, type, key, val):
        self._empty = False
        self._manual = True

        logging.debug("gamesync: add t=%s, k=%s, v=%s", type, key, val)
        if key is None or val is None:
            return

        if not key.isnumeric():
            key = self._fnv.get_hash(key)
        else:
            key = int(key)

        if val == '-': #any
            val = '0'
        if not val.isnumeric():
            val = self._fnv.get_hash(val)
        else:
            val = int(val)

        self.add(type, key, val)


    def _get_info(self, id):
        return _get_info(self._txtpcache, id)

# ---------------------------------------------------------

# saves possible switch paths in a txtp
class GamesyncPaths(object):

    def __init__(self, txtpcache):
        self._empty = True
        self._txtpcache = txtpcache
        self._root = _GamesyncNode(None, [], self._txtpcache)
        self._current = self._root
        self._params = None
        self._params_done = {}

    def is_empty(self):
        return self._empty

    # register path
    def adds(self, gamesyncs):
        node = _GamesyncNode(self._current, gamesyncs, self._txtpcache)

        self._current.append(node)
        self._current = node
        self._empty = False

        unreachable = self._is_unreachable()
        return unreachable

    def _is_unreachable(self):
        if not self._txtpcache.x_prefilter_paths:
            return False

        gamesyncs = self._current.elems
        node = self._current

        while True:
            node = node.parent
            if not node:
                break
            for type, name, value in gamesyncs:
                key = (type, name)
                value_prev = node.params.get(key)
                if value_prev and value_prev != value:
                    return True

        return False

    def add(self, type, name, value):
        return self.adds([(type, name, value)])

    # current path is done
    def done(self):
        self._current = self._current.parent

    # After registering all possible paths in a step, in some cases (mainly AkTree) we want to sort values
    # by name or otherwise names get a bit strange (m_11 1889767167 > m_01 1906544720). Groups are always
    # in order (as selected).
    # - CAkSwitchCntr: ordered (SwitchList)
    # - CAkMusicTrack: ordered (TrackSwitchAssoc)
    # - CAkMusicSwitchCntr (old): ordered?
    # - CAkMusicSwitchCntr (new): unordered (AkTree)
    # - CAkDialogueEvent (old): ordered?
    # - CAkDialogueEvent (new): unordered (AkTree)
    def sort(self, presorted=False):
        if not self._txtpcache.wwnames:
            return
        # by default uses pre-sorted order, unless forced
        if presorted and not self._txtpcache.wwnames.sort_always():
            return

        # uses GamesyncNode __lt__
        self._current.children.sort()

    def combos(self):
        if self._params is not None:
            return self._params

        # use registered info to build params
        self._params = []

        if DEBUG_PRINT_TREE_BASE:
            self._debug_print_tree_base()

        self._include_path(self._root)

        if DEBUG_PRINT_TREE_COMBOS:
            self._debug_print_tree_combos()

        return self._params

    def _include_path(self, node):
        if not node.children:
            # leaf node found, add all gamesyncs to path (in reverse to simplify)
            params = GamesyncParams(self._txtpcache)

            path_node = node
            while path_node:
                params.adds(path_node.elems)
                path_node = path_node.parent
                params._depth += 1

            if DEBUG_PRINT_TREE_MAKING:
                logging.debug("GS path added")

            # some paths are layers with repeated flags, ignore
            params_key = params.key()
            if params_key not in self._params_done:
                self._params_done[params_key] = True
                self._params.append(params)

        for child in node.children:
            self._include_path(child)

    def add_params(self, params):
        self._params = []
        for combo in params.combos():
            gparams = GamesyncParams(self._txtpcache)
            for item in combo:
                gparams.add_gsparam(item.type, item.key, item.val)
            self._params.append(gparams)

    # -----------------------------------------------------

    def _get_info(self, id):
        return _get_info(self._txtpcache, id)

    def _debug_print_tree_base(self):
        self._depth = 0
        self._leaf_count = 0
        logging.info("*** tree")
        self._debug_print_combos(self._root)
        logging.info(" >> (total %i)" % (self._leaf_count))
        logging.info("")

    def _debug_print_tree_combos(self):
        logging.info("*** combos")
        for path in self._params:
            elems = self._debug_print_elems(path.get_elems())
            logging.info(elems)
        logging.info(" >> (total %i)" % (len(self._params)))
        logging.info("")

    def _debug_print_combos(self, node):
        self._depth += 1
        for subnode in node.children:
            elems = self._debug_print_elems(subnode.elems)
            logging.info("%s%s", ' ' * self._depth * DEBUG_DEPTH_MULT, elems)
            if not subnode.children:
                self._leaf_count += 1
            self._debug_print_combos(subnode)
        self._depth -= 1

    def _debug_print_elems(self, elems):
        lines =['[']
        for elem in elems:
            if len(elem) == 2:
                type, name = elem
                lines.append('(%s,%s)' % (type, self._get_info(name)))
            else:
                type, name, value = elem
                lines.append('(%s,%s,%s)' % (type, self._get_info(name), self._get_info(value)))
        lines.append(']')
        return ''.join(lines)

