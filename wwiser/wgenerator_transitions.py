
# transition musicsegments in switches/playlists don't get used, register to generate at the end

class Transitions(object):
    def __init__(self, ncaller):
        self._root_ntid = None
        self._transition_nodes = {}
        if ncaller:
            self._caller_ntid = ncaller.find1(type='sid')

    def get_nodes(self):
        return self._transition_nodes.values()

    #--------------------------------------------------------------------------

    def add(self, node):
        if not node:
            return

        # save transition and a list of 'caller' nodes (like events) for info later
        key = id(node)
        items = self._transition_nodes.get(key)
        if items:
            return

        # could save name callers if transitions are generated globally
        #    callers = set()
        #    items = (node, callers)
        #else:
        #    items[1].add(self._caller_ntid)

        self._transition_nodes[key] = (self._caller_ntid, node)
        return
