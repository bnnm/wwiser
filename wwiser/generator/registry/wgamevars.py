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

        try:
            self.key = int(key)
        except:
            return

        # allowed special values (*=wwise's default, -=not set)
        if val == 'min' or val == 'max' or val == '*' or val == '-':
            pass
        else:
            try:
                val = float(val)
            except:
                return
        self.value = val

        self.ok = True

# ---------------------------------------------------------

# stores gamevars (rtpc) config
class GamevarsParams(object):
    def __init__(self):
        self._items = OrderedDict()
        self._fnv = wfnv.Fnv()

    def adds(self, elems):
        if not elems:
            return

        for elem in elems:
            parts = elem.split('=')
            if len(parts) != 2:
                continue
            key = parts[0]
            val = parts[1]

            if not key.isnumeric():
                keyname = key
                key = self._fnv.get_hash(key)
            else:
                keyname = None

            #TODO allow multiple
            if ',' in val:
                item = None
            else:
                item = GamevarItem(key, val, keyname)

            if not item or not item.ok:
                logging.info('parser: ignored incorrect gamevar %s', elem)
                continue
            self._items[item.key] = item

    def get_item(self, id):
        id = int(id)
        return self._items.get(id)

    def get_items(self):
        return self._items.values()
