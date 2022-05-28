from collections import OrderedDict

# transition musicsegments in switches/playlists don't get used, registered to generate at the end

class Transitions(object):
    def __init__(self):
        self._items = []
        self._done = OrderedDict()

    def get_items(self):
        return self._items

    #--------------------------------------------------------------------------

    def add(self, rules):
        for btrn in rules.ntrns:
            
            if btrn.tid in self._done:
                continue
            self._done[btrn.tid] = True
            self._items.append(btrn)
