import logging
import itertools
from collections import OrderedDict
from . import wparams
from ... import wfnv

MAX_COMBOS = 15

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
#
# Technically this list should exist as parts gamesync (in Wwise states are globals), but it's separate as
# sometimes it generates insteresting variations that aren't possible in regular cases. It also makes easier
# to handle state combos.
#
# Editor shows all possible values in Statechunks (ex. using "bgm" group has m01, m02...) but only those states
# that change something (not 0) are saved in .bnk

class StateChunkItem(object):
    def __init__(self):
        self.type = wparams.TYPE_STATE #used?
        self.group = None
        self.value = None
        self.group_name = None
        self.value_name = None
        self.unreachable = False

    def init_nstate(self, ngroup, nvalue):
        self.group = ngroup.value()
        self.group_name = ngroup.get_attr('hashname')
        self.value = nvalue.value()
        self.value_name = nvalue.get_attr('hashname')
        # save volume instead of config b/c repeated groups+values may use different config objects
        # (but same volume), and "val" tuple would be seen as different due to config, in the "not in" checks
        # these are only used for combos, while config should be extracted from node's volume states

    #TODO improve name handling
    def init_base(self, group, value, group_name=None, value_name=None, wwnames=None):
        self.group = group
        self.value = value
        # these params may come from external vars, try to get names from db
        if wwnames:
            row = wwnames.get_namerow(group)
            if row and row.hashname:
                self.group_name = row.hashname

            row = wwnames.get_namerow(value)
            if row and row.hashname:
                self.value_name = row.hashname

    # used with "not in"
    def __eq__(self, other):
        return (
            self.type == other.type and
            self.group == other.group and
            self.value == other.value
        )

    def __repr__(self):
        gn = self.group_name or str(self.group)
        vn = self.value_name or str(self.value)
        return str((gn,vn))

# ---------------------------------------------------------

# stores current selected statechunk path
class StateChunkParams(object):
    def __init__(self):
        self._elems = OrderedDict()
        self._unreachables = False
        pass

    def has_unreachables(self):
        return self._unreachables

    def adds(self, scparams):
        for scparam in scparams:
            self.add(scparam)

    def add(self, scitem):
        if scitem.group is None or scitem.value is None:
            return
        if scitem.unreachable:
            self._unreachables = True
        key = (scitem.group, scitem.value)
        self._elems[key] = scitem

    def get_states(self):
        return self._elems.values()

    def add_scparam(self, scitem):
        self.add(scitem)

# ---------------------------------------------------------

# saves possible volume paths in a txtp
class StateChunkPaths(object):

    def __init__(self, wwnames=None):
        self._elems = OrderedDict()
        self._forced_path = False
        self._unreachables = False
        self._unreachables_only = False
        self._params = None
        self._fnv = wfnv.Fnv()
        self._wwnames = wwnames

    def is_empty(self):
        return len(self._elems) == 0

    def has_unreachables(self):
        return self._unreachables

    def is_unreachables_only(self):
        return self._unreachables_only

    def set_unreachables_only(self):
        self._unreachables_only = True

    # register
    def adds(self, ngamesyncs):
        for ngroup, nvalue in ngamesyncs:
            self.add(ngroup, nvalue)

    def add(self, ngroup, nvalue):
        scitem = StateChunkItem()
        scitem.init_nstate(ngroup, nvalue)
        self._add_scstate(scitem)

    def _add_scstate(self, scitem):
        key = (scitem.type, scitem.group)
        if key not in self._elems:
            items = []
            # maybe should have a special value of "variable X set to other, non-silencing thing"?
            #val_default = (group, 0, group_name, None)
            #items.append(val_default)
            self._elems[key] = items

        #for scitem in self._elems[key]:
        #    if scitem not in self._elems[key]:
        #    self._elems[key].append(scitem)

        if scitem not in self._elems[key]:
            self._elems[key].append(scitem)


    def combos(self):
        if self._params is not None:
            return self._params

        # use registered info to build params
        self._params = []

        elems = self._elems.values()

        # combos of existing variables (order doesn't matter here)
        totals = 1
        for elem in elems:
            totals *= len(elem)

        if totals >= MAX_COMBOS:
            # in rare cases (ZoE HD) there are too many silence combos
            logging.info("generator: ignoring statechunk combo excess of %s (may need to pass manually)" % (totals))
            items = elems
        else:
            items = itertools.product(*elems)
        
        for item in items:
            scparam = StateChunkParams()
            scparam.adds(item)
            self._params.append(scparam)

        return self._params

    def generate_default(self, sccombos):
        # generate a base .txtp with all songs in some cases
        # - multiple states used like a switch, base playing everything = bad (MGR, Bayo2)
        #   music=m01 {s}=vocal=on,action=a + music=a {s}=vocal=off,action=a + ...
        # - single state used for on/off a single layer, base playing everything = good (AChain)
        #   music=m01 {s} + music=a {s}=vocal=on
        # * should not make default state if there is a single state but it's fixed due to current path
        #   music=a {s}=music=a

        if self._unreachables_only:
            return False

        # detect if the value is fixed due to current state (but only a single state for PK Arceus,
        # that combines one fixed value that adds some volume and other states that don't)
        if self._forced_path:
            #TODO: should detect if all combo params are set in current gsparams (pass external)
            if len(sccombos) == 1:
                return False
            #if gsparams and not gsparams.is_empty():
            #    all_set = True
            #    for sccombo in sccombos:
            #        pvalue = gsparams.current(vcombo....)
            #        if pvalue is None:
            #            all_set = False
            #    if not all_set:
            #        return False

        # multivars like in MGR probably don't need a base value, but Pokemon Legends Arceus does
        #if len(sccombos) >= 1:
        #    vcombo = sccombos[0]
        #    if len(vcombo.items()) > 1: #g1=v1 + g2=v2
        #        return False

        return True

    def filter(self, gsparams):
        #if self._unreachables_only: #needs to be re-filtered
        #    return
        if not gsparams or gsparams.is_empty():
            return

        # Sometimes you have a path like "bgm=a", and volume states with the game group like "bgm=b/c" -96db.
        # It'd be impossible to reach those volumes since "bgm" is fixed to "a", so adjust state list to
        # mark those unreachable and optionally add current value as reachable.
        # If path states are different both can mix just fine (like "music=a" + vstates like "bgm=b/c").
        #
        # Usually "unreachables" could be removed, but in rare cases they lead to interesting unused
        # variations of volumes (DMC5's bgm_m00_boss.bnk). Those are generated after all variable combos
        # for reachables are created, as it gives better names and dupes
        #
        # ex. em5900_bat_start would go first otherwise, plus em5900_bat_start would be also a dupe
        #    (path order is as defined)
        #   play_m00_boss_bgm (bgm_boss=em5900_intro_m00) {s}=(bgm_boss=em5900_intro_m00)
        #   play_m00_boss_bgm (bgm_boss=em5900_intro_m00) {s}=~(bgm_boss=em5900_bat_start) {d}
        #   play_m00_boss_bgm (bgm_boss=em5900_bat_start) {s}=(bgm_boss=em5900_bat_start)

        for key in self._elems.keys():
            gs_type, gs_group = key
            gs_value = gsparams.current(gs_type, gs_group)
            if gs_value is None:
                continue

            # "any" set means all volume states should be generated (DMC5's bgm_m07/03_stage.bnk)
            if gs_value == 0:
                continue

            # mark that current path is forced, as it affects defaults in some cases
            # (don't do it with "any" as could be another value; needed in some DMC5 cases)
            self._forced_path = True

            # Remove all that aren't current bgm=a. This may remove bgm=b, bgm=c and leave original bgm=a (with some volume).
            # If there wasn't a bgm=a, remove the key (so no {s} combos is actually generated).
            # Could also include itself like "(bgm=a) {s}=(bgm=a)" for clarity (todo: needs names)

            scitems = self._elems[key]

            curr_scitem = StateChunkItem()
            curr_scitem.init_base(gs_group, gs_value, wwnames=self._wwnames)

            # check and add itself for better names (can't use not-in since we don't know volume)
            curr_exists = False
            for scitem in scitems:
                if curr_scitem == scitem: #eq
                    curr_exists = True
            if not curr_exists:
                scitems.append(curr_scitem)

            for scitem in list(scitems): #clone for iteration+removal
                if scitem.value != gs_value:
                    scitem.unreachable = True
                    self._unreachables = True
                    #scitems.remove(scitem) #skipped externally

            #if not items:
            #    self._elems.pop(key)

    def add_params(self, params):
        self._params = []
        for combo in params.combos():
            scparams = StateChunkParams()
            for item in combo:
                scitem = self._make_scitem(item)
                if not scitem:
                    continue
                scparams.add_scparam(scitem)
            self._params.append(scparams)

    def _make_scitem(self, item):
        key = item.key
        val = item.val
        key_name = None
        val_name = None

        if val == '-': #any?
            return None

        if not key.isnumeric():
            #key_name = val
            key = self._fnv.get_hash(key)
        else:
            key = int(key)

        if not val.isnumeric():
            #val_name = val
            val = self._fnv.get_hash(val)
        else:
            val = int(val)

        # don't pass current var names since may have different caps in wwnames?
        scitem = StateChunkItem()
        scitem.init_base(key, val, group_name=key_name, value_name=val_name, wwnames=self._wwnames)
        return scitem
