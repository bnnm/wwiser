import logging, re
from ... import wfnv


DEBUG_PRINT_TREE_BASE = False
DEBUG_PRINT_TREE_COMBOS = False
DEBUG_PRINT_TREE_PARAMS = False
DEBUG_PRINT_TREE_MAKING = False
DEBUG_PRINT_TREE_TEXT = False
DEBUG_DEPTH_MULT = 2

TYPE_SWITCH = 0
TYPE_STATE = 1
TYPE_NAMES = {
    TYPE_SWITCH: 'SW',
    TYPE_STATE: 'ST',
}

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
#******************************************************************************

class _GamesyncNode(object):
    def __init__(self, parent, gamesyncs):
        self.parent = parent
        self.elems = gamesyncs #a list for nodes with multiple gamesyncs at once
        self.children = []

    def append(self, node):
        self.children.append(node)

#******************************************************************************

def _get_info(txtpcache, id):
    try:
        if not DEBUG_PRINT_TREE_TEXT or not txtpcache.wwnames:
            return id
    except AttributeError:
        return id
    row = txtpcache.wwnames.get_namerow(id)
    if row and row.hashname:
        #return "%s=%s" % (row.hashname, id)
        return "%s" % (row.hashname)
    else:
        return id


# saves possible switch paths in a txtp
class GamesyncPaths(object):

    def __init__(self, txtpcache):
        self._empty = True
        self._txtpcache = txtpcache
        self._root = _GamesyncNode(None, [])
        self._current = self._root

    def is_empty(self):
        return self._empty

    def adds(self, gamesyncs):
        #for gamesync in gamesyncs: #todo
        #    logging.info("GP added: %i, %i, %i" % gamesync)

        self._empty = False
        node = _GamesyncNode(self._current, gamesyncs)
        self._current.append(node)
        self._current = node

    def add(self, type, name, value):
        self.adds([(type, name, value)])


    def done(self):
        self._current = self._current.parent


    def _print_combos(self, node):
        self._depth += 1
        for subnode in node.children:
            elems = self._print_elems(subnode.elems)
            logging.info("%s%s", ' ' * self._depth * DEBUG_DEPTH_MULT, elems)
            if not subnode.children:
                self._leaf_count += 1
            self._print_combos(subnode)
        self._depth -= 1

    def combos(self):
        if DEBUG_PRINT_TREE_BASE:
            self._depth = 0
            self._leaf_count = 0
            logging.info("*** tree")
            self._print_combos(self._root)
            logging.info(" >> (total %i)" % (self._leaf_count))
            logging.info("")

        self._paths = []
        self._find_path(self._root)


        if DEBUG_PRINT_TREE_COMBOS:
            logging.info("*** combos")
            for path in self._paths:
                elems = self._print_elems(path.get_elems())
                logging.info(elems)
            logging.info(" >> (total %i)" % (len(self._paths)))
            logging.info("")

        return self._paths

    def _print_elems(self, elems):
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

    def _get_info(self, id):
        return _get_info(self._txtpcache, id)

    def _find_path(self, node):
        if not node.children:
            # leaf node found, add all gamesyncs to path (in reverse to simplify)
            path = GamesyncParams(self._txtpcache)

            path_node = node
            while path_node:
                path.adds(path_node.elems)
                path_node = path_node.parent
                path._depth += 1

            if DEBUG_PRINT_TREE_MAKING:
                logging.debug("GS path added")
            self._paths.append(path)

        for child in node.children:
            self._find_path(child)

#******************************************************************************

# stores current selected switch path
class GamesyncParams(object):

    def __init__(self, txtpcache):
        self._empty = True #public
        self._elems = {}
        self._txtpcache = txtpcache
        self._manual = False
        self._fnv = wfnv.Fnv()
        self._depth = 0 #infp

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

    def adds(self, gamesyncs):
        unreachables = False
        for gamesync in gamesyncs:
            unreachable = self.add(*gamesync)
            if unreachable:
                unreachables = True
        return unreachables


    # include new variable
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
            #TODO: test if actually useful
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
            logging.debug("generator: expected gamesync (%s, %s) not set" % (TYPE_NAMES[type], self._get_info(name)))
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

            #pop values to simulate dynamic changes, though shouldn't happen nor be needed
            #value = values.pop()

        logging.debug("gamesync: get %s, %s, %s" % (type, self._get_info(name), self._get_info(value)))
        return value

    def add_param(self, type, key, val):
        logging.debug("gamesync: add t=%s, k=%s, v=%s", type, key, val)
        if key is None or val is None:
            return
        if not key.isnumeric():
            key = self._fnv.get_hash(key)
        if val == '-': #any
            val = '0'
        if not val.isnumeric():
            val = self._fnv.get_hash(val)
        self.add(type, key, val)


    def set_params(self, params):
        self._empty = False #even if passed list is empty (to simulate "nothing set")
        self._manual = True #manual params behave a bit differently

        if not params:
            return

        # split '(key=var)(key=var)', as output by wwiser
        final_params = []
        for param in params:
            replaces = {')(':'):(', '][': ']:[', ')[': '):[', '](': ']:('}
            is_split = False
            for repl_key, repl_val in replaces.items():
                if repl_key in param:
                    param = param.replace(repl_key, repl_val)
                    is_split = True

            if is_split:
                splits = param.split(':')
                final_params += splits
            else:
                final_params.append(param)
        params = final_params

        pattern_st = re.compile(r"\((.+)=(.+)\)")
        pattern_sw = re.compile(r"\[(.+)=(.+)\]")
        for param in params:
            match = pattern_st.match(param)
            if match:
                key, val = match.groups()
                self.add_param(TYPE_STATE, key, val)

            match = pattern_sw.match(param)
            if match:
                key, val = match.groups()
                self.add_param(TYPE_SWITCH, key, val)

        if DEBUG_PRINT_TREE_PARAMS:
            logging.info("*** params")
            logging.info("in: %s", params)

            logging.info("out: %s", self._elems)
            logging.info("")

    def _get_info(self, id):
        return _get_info(self._txtpcache, id)
