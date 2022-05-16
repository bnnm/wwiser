# transition musicsegments in switches/playlists don't get used, register to generate at the end

class Transitions(object):
    def __init__(self):
        self._items = []
        #self._transition_nodes = {}

    def get_items(self):
        #return self._transition_nodes.values()
        return self._items

    #--------------------------------------------------------------------------

    def add(self, rules):
        self._items.extend(rules.ntrns)

        #TODO check is this is needed

        #if not node:
        #    return

        # save transition and a list of 'caller' nodes (like events) for info later
        #key = id(node)
        #items = self._transition_nodes.get(key)
        #if items:
        #    return

        ## could save name callers if transitions are generated globally
        ##    callers = set()
        ##    items = (node, callers)
        ##else:
        ##    items[1].add(self._caller_ntid)

        #self._transition_nodes[key] = node
        return
