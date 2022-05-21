# stingers are special musicsegments, registered to generate at the end

class Stingers(object):
    def __init__(self):
        self._items = {}
        self._done = set()


    def get_items(self):
        return self._items

    #--------------------------------------------------------------------------

    def add(self, stingerlist):
        for bstinger in stingerlist.stingers:

            #TODO improve single ordered set
            if bstinger in self._done:
                continue
            self._done.add(bstinger)
            self._items.append(bstinger)
        #self._items.extend(stingerlist.stingers)
