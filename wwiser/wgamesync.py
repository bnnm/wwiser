import logging, re
from . import wfnv


DEBUG_PRINT_TREE_TEXT = False
DEBUG_PRINT_TREE_BASE = False
DEBUG_PRINT_TREE_COMBOS = False
DEBUG_PRINT_TREE_PARAMS = False
DEBUG_PRINT_TREE_MAKING = False
DEBUG_DEPTH_MULT = 2

TYPE_SWITCH = 0
TYPE_STATE = 1
TYPE_NAMES = {
    TYPE_SWITCH: 'SW',
    TYPE_STATE: 'ST',
}

# GAMESYNCS' STATE/SWITCH PATHS
# Some objects depend on states/switches. When parsing a root node (ex. event), by default the
# generator tries to find and save all possible paths, for example (for a complex case):
#   (root) --> music=bgm1 --> act=st1   = path1
#          |              \-> act=st2   = path2
#          |
#          \-> music=bgm2 + section=01 --> act=* (any)  = path3
#          |
#          \-> music=bgm2 + section=02 --> act=st3      = path4
#
# The list is saved as a tree with nodes simulating the above (no .txtp is written). Once done, it creates
# combos of variables that make each path, and generates one .txtp per path now having those vars "active":
#   [music=bgm1, act=st1] >> txtp1
#   [music=bgm1, act=st2] >> txtp2
#   [music=bgm2, section=01, act=*] >> txtp3
#   [music=bgm2, section=02, act=st3] >> txtp4
#
# It's done this way to mimic Wwise, and to allow user set variables externally for certain config.
# Real gamesyncs are set global or per game object (so same event + vars changes by character),
# but there is no need to simulate that, as the generator acts like a global+game object.
#
# Final order shouldn't matter as vars are set to a single value (I hope):
#   music=bgm01 -> act=st1 + music=bgm02   (music can't be 2 things at the same time)
# This is possible though:
#   music=bgm01 -> act=st1 + music=*       (last node just expects "music" to be defined/set)
# The former wouldn't reach a valid node, but it's probably ok to have such paths in banks.
#
# You can have a "music" state and "music" switch that are named the same, as long as type
# (switch/state) is different, so vars are represented by [type + name/key + value].
#
# Some paths are only reachable using real-time changes:
#   (root) --> music=bgm1 --> music=bgm1 = path1
#                         \-> music=bgm2 = path2
# Since music starts at bgm1, path2 is only reachable if during audio music changes to bgm1.
#
# Rarely multiple paths can play at the same time:
#   event > play-action1 > music_a=bgm1 > ...
#         \ play-action2 > music_b=bgm1 > ...
# At the moment only one path can be active.
#
# Instead of saving paths, we could try to generate a combo of all possible variables too
# (like [music=bgm1 + act=st1 + section=02], even if unlikely). However some games use +30
# variables in some paths, so the amount of combos is too high. The current way is more
# complex to set up, though.
#
# Code populates tree like:
#
#   for ...
#       paths.add(gamesync1)                #starts sub-path
#       ... (calls to next audio object)
#           for ...
#               paths.add(gamesync2)        # starts sub-path
#                   ... (calls)
#               paths.done()                # ends sub-path
#       paths.done()                        #ends sub-path

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
    if not DEBUG_PRINT_TREE_TEXT or not txtpcache.wwnames:
        return id
    row = txtpcache.wwnames.get_namerow(id)
    if row and row.hashname:
        return "%s=%s" % (row.hashname, id)
    else:
        return id


# saves possible switch paths in a txtp
class GamesyncPaths(object):

    def __init__(self, txtpcache):
        self.empty = True
        self._txtpcache = txtpcache
        self._root = _GamesyncNode(None, [])
        self._current = self._root
        self.stingers = []

    def adds(self, gamesyncs):
        #for gamesync in gamesyncs: #todo
        #    logging.info("GP added: %i, %i, %i" % gamesync)

        self.empty = False
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
            #leaf node found, add all gamesyncs to path (in reverse to simplify, doesn't matter)
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

    def add_stingers(self, stingers):
        self.stingers.extend(stingers)

#******************************************************************************

# stores current selected switch path
class GamesyncParams(object):

    def __init__(self, txtpcache):
        self.empty = True #public
        self._elems = {}
        self._txtpcache = txtpcache
        self._manual = False
        self._fnv = wfnv.Fnv()
        self._depth = 0 #infp

    def get_elems(self):
        elems = []
        for key in self._elems:
            type, name = key
            values = self._elems[key]
            for value in values:
                elems.append((type, name, value))
        return elems

    def adds(self, gamesyncs):
        for gamesync in gamesyncs:
            self.add(*gamesync)


    #include new variable
    def add(self, type, name, value):
        self.empty = False

        type = int(type)
        name = int(name)
        value = int(value)

        key = (type, name)
        if key not in self._elems:
            self._elems[key] = []

        # vars are added to a list to (possibly) support paths that can only be reached
        # with dynamic changes (probably not needed? usually all values are available)
        # - switch music=bgm1 > (switch music=bgm1)
        #                     > (switch music=bgm2) **unreachable if music is always bgm1

        if DEBUG_PRINT_TREE_MAKING:
            logging.debug("GS added: %s%s, %s, %s" % (' ' * self._depth * DEBUG_DEPTH_MULT, type, self._get_info(name), self._get_info(value)))
        self._elems[key].append(value)

        return

    #get currently set single value of gamesync
    def value(self, type, name):
        key = (type, name)

        values = self._elems.get(key)
        if not values:
            #normally doesn't happen, but when multiple paths play at once, only one is active ATM
            # and other paths won't find their variables set
            # (ex. multiple play actions in event, or multiple switch-type tracks in a segment)
            logging.debug("generator: expected gamesync (%s, %s) not set" % (TYPE_NAMES[type], self._get_info(name)))
            self._txtpcache.multitrack += 1
            return None

        if self._manual and len(values) == 1:
            #don't pop last value in manual params (makes usage simpler)
            value = values[0]
        else:
            #pop values to simulate dynamic changes, though isn't normally necessary
            value = values.pop()
            #todo pop kills parallel playactions since first action will remove other actions's vars

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
        self.empty = False #even if passed list is empty (to simulate "nothing set")
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
