import itertools, logging, re
from collections import OrderedDict
from . import wgamesync


# Sometimes (ex. Platinum games), states control if musictracks must play or mute. It's silenced
# if state is set to a certain value (inverted meaning). If there are multiple states defined,
# then any of them may silence the object, and would play if state+value isn't set to target.
#
# To handle this, we save the silence states per object, plus all silence combos (separate from
# usual paths), then when making .txtp we set combos of those to mute parts.
#
# ex. musictracks + silence states in MGR "bgm_ev2000_end [bgm_Battle_Normal=default]"
# - stealth:        bgm_High_Low=High
# - action:         bgm_High_Low=Low    bgm_Vocal_BN=on     bgm_Zangeki=on
# - blade_mode:     bgm_High_Low=Low    bgm_Vocal_BN=on     bgm_Zangeki=off
# - vocal:          bgm_High_Low=Low    bgm_Vocal_BN=off
#
# No combo silences everything at once, or allows stealth + beat (most end up the same).
# Considering inverted meaning:
# - bgm_High_Low=low    bgm_Vocal_BN=*      bgm_Zangeki=*       = stealth
# - bgm_High_Low=High   bgm_Vocal_BN=off    bgm_Zangeki=off     = action
# - bgm_High_Low=High   bgm_Vocal_BN=off    bgm_Zangeki=on      = blade_mode
# - bgm_High_Low=High   bgm_Vocal_BN=on     bgm_Zangeki=*       = action
#
# If no variable is set everything would play at once. Not wanted in this example, but other songs
# (ex. Astral Chain) needs both non-set (plays all) and set (silences vocals) variations too.
# Most cases are simple "state set/not set" single variations
#
# To handle this we generate combos with all active variables:
# - bgm_High_Low=low, bgm_Vocal_BN=off, bgm_Zangeki=on
# - bgm_High_Low=low, bgm_Vocal_BN=on, bgm_Zangeki=on
# - bgm_High_Low=low, bgm_Vocal_BN=on, bgm_Zangeki=off
# - ...
# Typically only one variable is used though.

# saves possible silence paths in a txtp
class SilencePaths(object):

    def __init__(self):
        self.empty = True
        self._elems = OrderedDict()
        pass

    def add_nstates(self, ngamesyncs):
        for ngroup, nvalue, config in ngamesyncs:
            self._add_state(ngroup, nvalue, config)

    def _add_state(self, ngroup, nvalue, config):
        self.empty = False
        group = ngroup.value()
        group_name = ngroup.get_attr('hashname')
        value = nvalue.value()
        value_name = nvalue.get_attr('hashname')

        key = (wgamesync.TYPE_STATE, group)
        val = (group, value, group_name, value_name, config)
        if key not in self._elems:
            items = []
            # maybe should have a special value of "variable X set to other, non-silencing thing"?
            #val_default = (group, 0, group_name, None)
            #items.append(val_default)
            self._elems[key] = items

        if val not in self._elems[key]:
            self._elems[key].append(val)

    def combos(self):
        self._paths = []

        # short items by value_name if possible as it makes more consistently named .txtp
        # must order keys too since they same vars move around between tracks
        # order is value_name first then value (to avoid comparing str vs int), using '~' to force Nones go last
        elems = []
        for values in self._elems.values():
            values.sort(key=lambda x: (x[3] or '~', x[1])) #value
            elems.append(values)
        elems.sort(key=lambda x: (x[0][2] or '~', x[0][1])) #group

        # combos of existing variables
        #items = itertools.product(*self._elems.values())
        items = itertools.product(*elems)
        for item in items:
            sparam = SilenceParams()    
            sparam.adds(item)
            self._paths.append(sparam)

        return self._paths

#******************************************************************************

# stores current selected silence path
class SilenceParams(object):
    def __init__(self):
        self._elems = OrderedDict()
        pass

    def adds(self, vparams):
        for vparam in vparams:
            self.add(*vparam)

    def add(self, group, value, group_name, value_name, config):
        if group is None or value is None:
            return
        self._elems[(group, value)] = (group, value, group_name, value_name, config)

    def get_volume_state(self, nstates):
        #key = (type, name)
        for ngroup, nvalue, config in nstates:
            group = ngroup.value()
            value = nvalue.value()
            if (group, value) in self._elems:
                return config
            #if (group, 0) in self._elems:
            #    return True
        return None

    def items(self):
        items = []
        for group, value, group_name, value_name, _ in self._elems.values():
            items.append((group, value, group_name, value_name))
        return items
