import logging
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
        self.is_default = val == '-'

        if self.is_min or self.is_max or self.is_default:
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

    def add(self, item):
        if not item:
            return
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
        self._combos = []
        self._fnv = wfnv.Fnv()

    # no registers needed

    def combos(self):
        return self._combos

    # ---

    def add_params(self, params):
        for combo in params.combos():
            gparams = GamevarsParams()
            for item in combo:
                gitem = self._make_gitem(item)
                gparams.add(gitem)
            self._combos.append(gparams)

    def _make_gitem(self, item):
        key = item.key
        val = item.val

        if key == '*': #special
            keyname = None
        elif not key.isnumeric():
            keyname = key
            key = self._fnv.get_hash(key)
        else:
            keyname = None

        gitem = GamevarItem(key, val, keyname)
        if not gitem.ok:
            logging.info('parser: ignored incorrect gamevar %s', item.elem)
            return None

        return gitem
