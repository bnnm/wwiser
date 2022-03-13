import itertools, logging, re
from collections import OrderedDict
from . import wgamesync


# Sometimes (ex. Platinum games) set states control volumes, so musictracks must play or mute.
# Usually if state is set volume becomes -96db (silenced) but it's also used to increase/decrease
# certain layer's volume. If multiple states are defined, they work separate and any of them is
# possible.
#
# To handle this, we save the volume states per object, plus all combos (separate from usual
# paths), then when making .txtp we set combos of those to change volume in some parts.
#
# ex. musictracks + silence states in MGR "bgm_ev2000_end [bgm_Battle_Normal=default]"
# - stealth:        bgm_High_Low=High
# - action:         bgm_High_Low=Low    bgm_Vocal_BN=on     bgm_Zangeki=on
# - blade_mode:     bgm_High_Low=Low    bgm_Vocal_BN=on     bgm_Zangeki=off
# - vocal:          bgm_High_Low=Low    bgm_Vocal_BN=off
#
# No combo silences everything at once, or allows stealth + beat (most end up the same).
# Considering silenced meaning:
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

# saves possible volume paths in a txtp
class SilencePaths(object):

    def __init__(self):
        self._elems = OrderedDict()
        self._forced_path = False
        pass

    def is_empty(self):
        return len(self._elems) == 0

    def add_nstates(self, ngamesyncs):
        for ngroup, nvalue, config in ngamesyncs:
            self._add_nstate(ngroup, nvalue, config)

    def _add_nstate(self, ngroup, nvalue, config):
        group = ngroup.value()
        group_name = ngroup.get_attr('hashname')
        value = nvalue.value()
        value_name = nvalue.get_attr('hashname')
        volume_state = 0
        if config and config.volume: 
            volume_state = config.volume
        # save volume instead of config b/c repeated groups+values may use different config objects
        # (but same volume), and "val" tuple would be seen as different due to config, in the "not in" checks
        # these are only used for combos, while config should be extracted from node's volume states
        self._add_state(group, value, group_name, value_name, volume_state)

    def _add_state(self, group, value, group_name, value_name, volume_state):

        key = (wgamesync.TYPE_STATE, group)
        val = (group, value, group_name, value_name, volume_state)
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

    def generate_default(self, combos):
        # generate a base .txtp with all songs in some cases
        # - multiple states used like a switch, base playing everything = bad (MGR, Bayo2)
        #   music=m01 {s}=vocal=on,action=a + music=a {s}=vocal=off,action=a + ...
        # - single state used for on/off a single layer, base playing everything = good (AChain)
        #   music=m01 {s} + music=a {s}=vocal=on
        # * should not make default state if there is a single state but it's fixed due to current path
        #   music=a {s}=music=a
        #return True

        #if len(self._elems) != 1: #would need to check sub-groups
        #    return False
        if len(combos) != 1:
            return False

        # detect if the value is fixed due to current state
        if self._forced_path:
            return False

        return True

    def filter(self, pparams, fake_multiple=False):
        if not pparams or pparams.empty:
            return

        # Sometimes you have a path like "bgm=a", and volume states with the game group like "bgm=b/c" -96db.
        # It'd be impossible to reach those volumes since "bgm" is fixed to "a", so adjust state list.
        # If path is different both can mix just fine (like "music=a" + vstates like "bgm=b/c").
        # This fixes some games like DMC5 that use stuff like:
        #  (bgm_boss=em5200_bat_start) {s}=(bgm_boss=em5200_bat_start) > silences battle layer
        #  (bgm_boss=em5200_trueform) {s} > same path but doesn't silence battle layer

        for key in self._elems.keys():
            _, group = key
            pvalue = pparams.current(*key)
            if pvalue is None:
                continue
            # "any" set means all silence states should be generated (DMC5's bgm_07_stage.bnk)
            if pvalue == 0:
                #todo force output base? creates some odd base txtp with unlikely volume in play_m07_bgm
                continue

            # this allows forced/current value to coexist with others, resulting in fake combos, but may be interesting
            # in some cases for unused varitions? But it also created dupes in wrong ways:
            # * without fake_multiple makes:
            #   play_m04_boss_bgm (bgm_boss=em5200_bat_start) {s}=(bgm_boss=em5200_bat_start)
            # * with fake_multiple makes:
            #   play_m04_boss_bgm (bgm_boss=em5200_bat_start) {s}=(bgm_boss=em5200_bat_end)
            #   play_m04_boss_bgm (bgm_boss=em5200_bat_start) {s}=(bgm_boss=em5200_bat_start) [dupe of the above]
            if fake_multiple:
                self._add_state(group, pvalue, None, None, None) # todo: needs names#
                return

            # Remove all that aren't current bgm=a. This may remove bgm=b, bgm=c and leave original bgm=a (with some volume).
            # If there wasn't a bgm=a, remove the key (so no {s} combos is actually generated).
            # Could also include itself like "(bgm=a) {s}=(bgm=a)" for clarity (todo: needs names)

            # mark that current path is forced, as it affects defaults in some cases
            self._forced_path = True

            items = self._elems[key]
            for item in list(items): #clone for proper iteration+removal
                _, vvalue, _, _, _ = item
                if vvalue != pvalue:
                    items.remove(item)

            if not items:
                self._elems.pop(key)
                #self._add_state(group, pvalue, None, None, None) # optionally include itself?


#******************************************************************************

# stores current selected silence path
class SilenceParams(object):
    def __init__(self):
        self._elems = OrderedDict()
        pass

    def adds(self, vparams):
        for vparam in vparams:
            self.add(*vparam)

    def add(self, group, value, group_name, value_name, volume):
        if group is None or value is None:
            return
        self._elems[(group, value)] = (group, value, group_name, value_name, volume)

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
