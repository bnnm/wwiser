import logging
from collections import OrderedDict
from .. import wfnv



# GAMESYNCS' GAME PARAMETERS (gamevars)
# Cets config used for RTPCs (Real Time Parameter Control), like battle_rank or
# player_distance, typically to control volumes/pitches/etc via in-game values.

class GamevarItem(object):
    def __init__(self, key, val, keyname=None):
        self.ok = False
        self.key = None
        self.value = None
        self.min = False
        self.max = False
        self.keyname = keyname

        try:
            self.key = int(key)
        except:
            return

        if val == 'min':
            self.value = 0.0
            self.min = True
        elif val == 'max':
            self.value = 0.0
            self.max = True
        elif not val:
            val = 0.0
        else:
            try:
                val = float(val)
            except:
                return
        self.value = val

        self.ok = True

    def info(self):
        key = self.keyname or self.key
        val = self.value or 0.0
        if self.min:
            val = 'min'
        elif self.max:
            val = 'max'
        return "%s=%s" % (key, val)

# stores gamevars (rtpc) config
class GamevarsParams(object):
    def __init__(self):
        self.active = False
        self._items = OrderedDict()
        self._fnv = wfnv.Fnv()
        #self._info = ''

    def add(self, elems):
        if not elems:
            return

        self.active = True
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

            if ',' in val:
                item = None
            else:
                item = GamevarItem(key, val, keyname)

            if not item or not item.ok:
                logging.info('parser: ignored incorrect gamevar %s', elem)
                continue

            #self._info += elem + ' ' 
            self._items[item.key] = item
        #self._info = self._info.strip()

    def get_info(self):
        info =''
        for item in self._items.values():
            info += item.info() + ' '

        #return self._info
        return info.strip()

    def is_value(self, id):
        id = int(id)
        return id in self._items

    def get_item(self, id):
        id = int(id)
        return self._items.get(id)
