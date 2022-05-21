import logging, itertools
from collections import OrderedDict
from ... import wfnv


# GAMESYNCS' GAME PARAMETERS (gamevars)
# Sets config used for RTPCs (Real Time Parameter Control), like battle_rank or
# player_distance, typically to control volumes/pitches/etc via in-game values.

class GamevarItem(object):
    def __init__(self, key, val, keyname=None):
        self.ok = False
        self.key = None
        self.value = None
        self.keyname = keyname

        # special key that sets all gamevars to this
        if key == '*':
            self.key = 0
        else:
            try:
                self.key = int(key)
            except:
                return

        # allowed special values
        self.is_min = val == 'min'
        self.is_max = val == 'max'
        self.is_default = val == '*'
        self.is_unset = val == '-'

        if self.is_min or self.is_max or self.is_default or self.is_unset:
            pass #val = 0 #don't change to detect dupes
        else:
            try:
                val = float(val)
            except:
                return #invalid
        self.value = val

        self.ok = True

# ---------------------------------------------------------

# stores gamevars (rtpc) config
class GamevarsParams(object):
    def __init__(self):
        self._items = OrderedDict()

    def adds(self, items):
        if not items:
            return

        for item in items:
            self._items[item.key] = item

    def get_item(self, id):
        id = int(id)
        return self._items.get(id)

    def get_items(self):
        return self._items.values()

# ---------------------------------------------------------

# stores combos of gamevars (rtpc) config
class GamevarsPaths(object):
    def __init__(self):
        self._items = OrderedDict()
        self._combos = []
        self._fnv = wfnv.Fnv()

    def adds(self, elems):
        if not elems:
            return

        # this allows making combos in the form of:
        # bgm=m01 > bgm=m01
        # bgm=m01 sfx=s01 > bgm=m01 sfx=s01
        # bgm=m01,m02 > bgm=m01 / bgm=m01
        # bgm=m01,m02 + sfx=s01,s02 > bgm=m01 sfx=s01 / bgm=m01 sfx=s02 / bgm=m02 sfx=s01 / bgm=m02 sfx=s02

        for elem in elems:
            parts = elem.split('=')
            if len(parts) != 2:
                continue
            key = parts[0]
            val = parts[1]

            if key == '*': #special
                keyname = None
            elif not key.isnumeric():
                keyname = key
                key = self._fnv.get_hash(key)
            else:
                keyname = None

            if ',' in val:
                item = None
                subvals = val.split(",")
                for subval in subvals:
                    item = GamevarItem(key, subval, keyname)
                    self._add_item(item, elem)
            else:
                item = GamevarItem(key, val, keyname)
                self._add_item(item, elem)

        # make possible combos
        itemproduct = itertools.product(*self._items.values())
        for itemlist in itemproduct:
            gvparams = GamevarsParams()
            gvparams.adds(itemlist)
            self._combos.append(gvparams)

    def _add_item(self, item, elem):
        if not item or not item.ok:
            logging.info('parser: ignored incorrect gamevar %s', elem)
            return

        if item.key not in self._items:
            self._items[item.key] = []
        items = self._items[item.key]
        for old_item in items:
            if old_item.value == item.value:
                return
        items.append(item)

    def combos(self):
        return self._combos
