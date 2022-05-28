import logging, itertools
import itertools
from collections import OrderedDict


TYPE_SWITCH = 0 #official Wwise
TYPE_STATE = 1 #official Wwise
TYPE_GAMEPARAMETER = 2 #made up
TYPE_NAMES = {
    TYPE_SWITCH: 'SW',
    TYPE_STATE: 'ST',
    TYPE_GAMEPARAMETER: 'GP',
}

# Stores a simple list of params (gamesyncs/gamevars/statechunks) with extra config,
# that will be passed later to each final list. Allow combos in the form of:
# "(bgm=m01)[bgm=m01] {bgm=1.0}" > [ST bgm=m01, SW bgm=m01, GP hp=1.0]
# "bgm=m01 sfx=s01" > [ST bgm=m01, ST sfx=s01] (when defaulting to ST)
# "bgm=m01 / bgm m02" > [ST bgm=m01] / [ST bgm=m01]
# "bgm=m01,m02" > [ST bgm=m01] / [ST bgm=m01]
# "bgm=m01,m02 sfx=s01,s02" > [bgm=m01 sfx=s01], [bgm=m01 sfx=s02], [bgm=m02 sfx=s01], [bgm=m02 sfx=s02]
# "bgm=m01,m02 sfx=s01 / sfx=s02" > [bgm=m01 sfx=s01], [bgm=m02 sfx=s01], [sfx=s02]

class ParamItem(object):
    def __init__(self, type, key, val, elem):
        self.type = type
        self.key = key
        self.val = val
        self.elem = elem #original

    def __repr__(self):
        return "%s:%s=%s" % (TYPE_NAMES.get(self.type), self.key, self.val)

# ---------------------------------------------------------

class Params(object):
    def __init__(self, allow_st=False, allow_sw=False, allow_gp=False):
        self._allow_st = allow_st
        self._allow_sw = allow_sw
        self._allow_gp = allow_gp

        self._items = OrderedDict() #current type/key > items
        self._combos = [] #N lists of items
        # example: "bgm=m01,m02 / sfx=s01 / bgm=m01,m02 sfx=s01" = 5 combos
        # [
        #   (bgm=m01),
        #   (bgm=m02),
        #   (sfx=s01),
        #   (bgm=m01, sfx=s01),
        #   (bgm=m02, sfx=s01),
        # ]

    def _add_item(self, item, subval=False):
        # handle subvals (bgm=val1,val2) in a list of [bgm=val1, bgm=val2], while regular
        # repeats (bgm=val1 bgm=val2) just overwrite and have a single-item list of [bgm=val2]
        index = (item.type, item.key)

        # maybe should compare key fnv (taking into account special var *), unlikely to mix hashname and sid though
        exists = index in self._items
        if not exists:
            self._items[index] = []
        items = self._items[index]
        
        # no repeats in 
        if not subval and exists:
            items.clear()

        # allow repeats but of different value
        if subval:
            for old_item in items:
                if old_item.val == item.val:
                    return

        items.append(item)


    def _add_param(self, elem):
        if not elem:
            return False

        sted = (elem[0], elem[-1])
        if   sted == ('(', ')'):
            type = TYPE_STATE
        elif sted == ('[', ']'):
            type = TYPE_SWITCH
        elif sted == ('{', '}'):
            type = TYPE_GAMEPARAMETER
        else:
            type = None

        if type is not None:
            keyval = elem[1:-1]
        else:
            keyval = elem
            # default with 1 allowed type
            if   self._allow_st and not self._allow_sw and not self._allow_gp:
                type = TYPE_STATE
            elif not self._allow_st and self._allow_sw and not self._allow_gp:
                type = TYPE_SWITCH
            elif not self._allow_st and not self._allow_sw and self._allow_gp:
                type = TYPE_GAMEPARAMETER

        if type is None:
            return

        parts = keyval.split('=')
        if len(parts) != 2:
            return False
        key = parts[0]
        val = parts[1]

        if ',' in val:
            item = None
            subvals = val.split(",")
            for subval in subvals:
                item = ParamItem(type, key, subval, elem)
                self._add_item(item, subval=True)
        else:
            item = ParamItem(type, key, val, elem)
            self._add_item(item)

        return True


    def adds(self, elems):
        if not elems:
            return

        # separate vars, could be improved
        replaces = {
            ')(':'):(', ')[':'):[', '){':'):{',
            '](':']:(', '][':']:[', ']{':']:{', 
            '}(':'}:(', '}[':'}:[', '}{':'}:{', 
        }

        for elem in elems:
            if elem == '/': # new sublist bgm=a1 / bgm=a2
                self._add_combos()
                continue

            is_split = False
            for repl_key, repl_val in replaces.items():
                if repl_key in elem:
                    elem = elem.replace(repl_key, repl_val)
                    is_split = True
            if is_split:
                splits = elem.split(':')
                for split in splits:
                    ok = self._add_param(split)
                    if not ok:
                        logging.info('parser: ignored incorrect param %s', split)

            else:
                ok = self._add_param(elem)
                if not ok:
                    logging.info('parser: ignored incorrect param %s', elem)

        self._add_combos()

    def _add_combos(self):
        # make possible combos of current items
        itemproducts = list(itertools.product(*self._items.values()))
        for itemproduct in itemproducts:
            #itemproduct = list(itemproduct) #these are tuples but no matter
            self._combos.append(itemproduct)
        self._items.clear() #in case of more lists

    def combos(self):
        return self._combos
