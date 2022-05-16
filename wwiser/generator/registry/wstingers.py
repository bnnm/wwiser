# stingers are special musicsegments, register to generate at the end

class Stingers(object):
    def __init__(self):
        self._items = []

    def get_items(self):
        return self._items

    #--------------------------------------------------------------------------

    def add(self, stingerlist):
        self._items.extend(stingerlist.stingers)
