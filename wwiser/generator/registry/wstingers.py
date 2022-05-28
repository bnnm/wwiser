from collections import OrderedDict

# stingers are special musicsegments, registered to generate at the end

class Stingers(object):
    def __init__(self):
        self._items = []
        self._done = OrderedDict()


    def get_items(self):
        return self._items

    #--------------------------------------------------------------------------

    def add(self, stingerlist):
        for bstinger in stingerlist.stingers:

            if bstinger in self._done:
                continue
            self._done[bstinger] = True
            self._items.append(bstinger)
