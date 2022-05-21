# transition musicsegments in switches/playlists don't get used, registered to generate at the end

class Transitions(object):
    def __init__(self):
        self._items = []
        self._done = set()
        #self._transition_nodes = {}

    def get_items(self):
        #return self._transition_nodes.values()
        return self._items

    #--------------------------------------------------------------------------

    def add(self, rules):
        for btrn in rules.ntrns:
            
            #TODO improve single ordered set
            if btrn in self._done:
                continue
            self._done.add(btrn)
            self._items.append(btrn)

        #self._items.extend(rules.ntrns)

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
