import itertools
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
#
# Technically this list should exist as parts gamesync (in Wwise states are globals), but it's separate as
# sometimes it generates insteresting variations that aren't possible in regular cases. It also makes easier
# to handle state combos.

class StateChunkItem(object):
    def __init__(self):
        self.type = wgamesync.TYPE_STATE
        self.group = None
        self.value = None
        self.group_name = None
        self.value_name = None
        self.volume_state = 0
        self.unreachable = False

    def init_nstate(self, ngroup, nvalue, config):
        self.group = ngroup.value()
        self.group_name = ngroup.get_attr('hashname')
        self.value = nvalue.value()
        self.value_name = nvalue.get_attr('hashname')
        # save volume instead of config b/c repeated groups+values may use different config objects
        # (but same volume), and "val" tuple would be seen as different due to config, in the "not in" checks
        # these are only used for combos, while config should be extracted from node's volume states
        if config and config.volume: 
            self.volume_state = config.volume

    def init_base(self, group, value, wwnames):
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

    def eq_base(self, other):
        return (
            self.type == other.type and 
            self.group == other.group and 
            self.value == other.value
        )

    def eq_vol(self, other):
        return (
            self.type == other.type and 
            self.group == other.group and 
            self.value == other.value
        )

    # used with "not in"
    def __eq__(self, other):
        return self.eq_vol(other)

    def __repr__(self):
        gn = self.group_name or str(self.group)
        vn = self.value_name or str(self.value)
        vs = str(self.volume_state)
        return str((gn,vn,vs))
        

# saves possible volume paths in a txtp
class StateChunkPaths(object):

    def __init__(self):
        self._elems = OrderedDict()
        self._forced_path = False
        self._unreachables = False
        self._unreachables_only = False
        pass

    def is_empty(self):
        return len(self._elems) == 0

    def has_unreachables(self):
        return self._unreachables

    def is_unreachables_only(self):
        return self._unreachables_only

    def set_unreachables_only(self):
        self._unreachables_only = True

    def add_nstates(self, ngamesyncs):
        for ngroup, nvalue, config in ngamesyncs:
            scitem = StateChunkItem()
            scitem.init_nstate(ngroup, nvalue, config)
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
        self._paths = []

        # short items by name if possible as it makes more consistently named .txtp
        # must order keys too since they same vars move around between tracks
        # Uses tuples to avoid comparing str vs int), using '~' to force Nones go last
        # If item is marked as unreachable, must go after all reachables
        elems = []
        for values in self._elems.values():
            values.sort(key=lambda x: (not x.unreachable, x.value_name or '~', x.value))
            elems.append(values)

        elems.sort(key=lambda x: (not x[0].unreachable, x[0].group_name or '~', x[0].group))

        # combos of existing variables
        #items = itertools.product(*self._elems.values())
        items = itertools.product(*elems)
        for item in items:
            scparam = StateChunkParams()    
            scparam.adds(item)
            self._paths.append(scparam)

        return self._paths

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

        # multivars like in MGR probably don't need a base value
        # but Pokemon Legends Arceus does :(
        #if len(sccombos) >= 1:
        #    vcombo = sccombos[0]
        #    if len(vcombo.items()) > 1: #g1=v1 + g2=v2
        #        return False

        return True

    def filter(self, gsparams, wwnames=None):
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
            _, group = key
            pvalue = gsparams.current(*key)
            if pvalue is None:
                continue

            # "any" set means all volume states should be generated (DMC5's bgm_07_stage.bnk)
            if pvalue == 0:
                #todo force output base instead of generate_default? needs to be reordered so it goes last
                continue

            # mark that current path is forced, as it affects defaults in some cases, except when using "any"
            # (this creates a useless base {s} in some cases but it's needed in others)
            self._forced_path = True

            # Remove all that aren't current bgm=a. This may remove bgm=b, bgm=c and leave original bgm=a (with some volume).
            # If there wasn't a bgm=a, remove the key (so no {s} combos is actually generated).
            # Could also include itself like "(bgm=a) {s}=(bgm=a)" for clarity (todo: needs names)

            scitems = self._elems[key]

            curr_scitem = StateChunkItem()
            curr_scitem.init_base(group, pvalue, wwnames) #todo improve name handling

            # check and add itself for better names (can't use not-in since we don't know volume)
            curr_exists = False
            for scitem in scitems:
                if curr_scitem.eq_base(scitem):
                    curr_exists = True
            if not curr_exists:
                scitems.append(curr_scitem)

            for scitem in list(scitems): #clone for iteration+removal
                if scitem.value != pvalue:
                    scitem.unreachable = True
                    self._unreachables = True
                    #scitems.remove(scitem) #skipped externally

            #if not items:
            #    self._elems.pop(key)

#******************************************************************************

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

    def get_volume_states(self, nstates):
        configs = []
        for ngroup, nvalue, config in nstates:
            group = ngroup.value()
            value = nvalue.value()
            if (group, value) in self._elems:
                configs.append(config)
        return configs

    def items(self):
        return self._elems.values()
