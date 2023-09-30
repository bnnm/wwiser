import fnmatch, logging, os
from .. import wfnv

# filter applies to "outer" (base HIRC) objects
_MODE_OUTER = 0
# filter applies to "inner" (part of another object) objects
_MODE_INNER = 1
# filter applies to "unused" (not called by other objects) objects
_MODE_UNUSED = 2
#_MODE_UNUSED_INNER = 3

class GeneratorFilterItem(object):
    def __init__(self, value):
        # whether when node matches this filter node is included or excluded
        self.excluded = False
        # filter classification
        self.mode = _MODE_OUTER
        # filter must compare value vs different things. 
        self.use_sid = False
        self.use_class = False
        self.use_bank = False
        self.use_index = False
        # if value matches a pattern
        self.is_pattern = False
        # actual filter
        self.value = None
        self.value_index = None #for index

        value = value.lower()

        value = value.split('#')[0] #remove comments

        if value.startswith('~'):
            self.mode = _MODE_UNUSED
            value = value[1:]

        if value.startswith('@'):
            self.mode = _MODE_INNER
            value = value[1:]

        if value.startswith('-') or value.startswith('/') :
            self.excluded = True
            value = value[1:]

        self.value = value

        # special mark
        if '*' in value:
            self.is_pattern = True

        # detect type of filter
        if value.isnumeric():
            # 123456789
            self.use_sid = True

        elif value.startswith('cak'):
            # CAk(type)
            self.use_class = True

        elif value.endswith('.bnk'):
            # (bankname).bnk
            self.use_bank = True

            # compare (name).bnk as (hash).bnk when no wildcards are used, to improve detection
            if not self.is_pattern:
                value_bank, __ = os.path.splitext(value)
                if not value_bank.isnumeric():
                    bankhash = wfnv.Fnv().get_hash(value_bank)
                    self.value = '%s.bnk' % (bankhash)

        elif '-' in value:
            # (bankname or bank hashname)-(index)-(description)
            self.use_index = True
            # ignore errors
            parts = value.split('-')
            bankname = parts[0]
            index = parts[1].split('~')[0] #remove possible extra parts
            self.value = self.get_bankcomp(bankname + '.bnk')
            self.value_index = int(index)

        else:
            # event names
            pass

        return

    def get_bankcomp(self, bankname):
        if self.is_pattern:
            return bankname

        # use bank's hash when no wildcards are used, to improve detection
        bankbase, __ = os.path.splitext(bankname)
        if bankbase.isnumeric():
            return bankname
        bankhash = wfnv.Fnv().get_hash(bankbase)
        return '%s.bnk' % (bankhash)

    def match(self, sid, hashname, classname, bankname, index):

        # filter's accepted value
        value = self.value

        # depending on filter, set things to compare (comps)
        if   self.use_sid:
            comps = [str(sid)]
        elif self.use_bank:
            comps = [self.get_bankcomp(bankname)]
        elif self.use_class:
            comps = [classname]
        elif self.use_index:
            # index needs multiple fields, check index here and bank below
            if self.value_index != index:
                return False
            comps = [self.get_bankcomp(bankname)]
        else:
            comps = [str(sid), hashname] # bnk and hashnames sometimes clash

        # test desined external comp vs current item's filter value
        for comp in comps:
            if not comp:
                continue
            comp = comp.lower()
            if self.is_pattern and fnmatch.fnmatch(comp, value):
                return True
            elif comp == value:
                return True

        return False

class GeneratorFilterConfig(object):
    def __init__(self, mode, filters):
        self.mode = mode
        self.allow_all_objects = False
        self.default_allow = False
        self.filters = []
        self._load(filters)

    def _load(self, filters):
        has_includes = False
        has_all = False
        for filter in filters:
            if self.mode != filter.mode:
                continue

            self.filters.append(filter)

            if not filter.excluded:
                has_includes = True
            if filter.use_class:
                has_all = True
            if filter.use_sid and not filter.excluded:
                has_all = True

        # if filter only has "includes", default must be "exclude everything but these",
        # while only "excludes" default is "include everything but these".
        # If both are set, first has priority (?).
        if has_includes:
            self.default_allow = False
        else:
            self.default_allow = True

        # unused + filter should not generate anything unless some filter is set (does weird stuff otherwise)
        if self.mode in [_MODE_UNUSED] and not self.filters:
            self.default_allow = False

        # for outer nodes, by default only Event types are generated (allow_all_objects is false).
        # for inner/unused nodes, by default all objects are generated (allow_all_objects is true).
        self.allow_all_objects = self.mode in [_MODE_INNER, _MODE_UNUSED]
        if has_all:
            # filtering by class or id means generating all
            self.allow_all_objects = True

        return

class GeneratorFilter(object):
    def __init__(self):
        self.active = False
        self._default_hircs = []
        self._cfgs = {}
        self.generate_rest = False # flag only: generate rest after filtering (rather than just filtered nodes)
        self.skip_normal = False # flag only: generate but don't write normal files
        self.skip_unused = False # flag only: generate but don't write unused files

    def set_default_hircs(self, items):
        self._default_hircs = items

    def add(self, items):
        if not items:
            return

        self.active = True

        filters = []
        for item in items:
            try:
                gfi = GeneratorFilterItem(item)
                filters.append(gfi)
            except:
                logging.info("filter: ignored %s", item)

        self._cfgs[_MODE_OUTER] = GeneratorFilterConfig(_MODE_OUTER, filters)
        self._cfgs[_MODE_INNER] = GeneratorFilterConfig(_MODE_INNER, filters)
        self._cfgs[_MODE_UNUSED] = GeneratorFilterConfig(_MODE_UNUSED, filters)
        return

    def _allow(self, mode, node, nsid=None, hashname=None, classname=None, bankname=None, index=None, bnode=None):
        if not nsid:
            nsid = node.find1(type='sid')
        if not nsid:
            return False
        sid = str(nsid.value())

        hashname = hashname or nsid.get_attr('hashname')
        if hashname:
            hashname = hashname.lower()
        classname = classname or node.get_name().lower()
        bankname = bankname or node.get_root().get_filename().lower()
        index = index or node.get_attr('index')
        if mode == _MODE_INNER and classname == 'caksound':
            hashname = bnode.sound.nsrc.get_attr('guidname')

        cfg = self._cfgs[mode]

        if not cfg.allow_all_objects and classname not in self._default_hircs:
            return False

        # inner filtering "excludes" works ok, but "includes" only apply to sounds (otherwise would filter whole branches)
        if mode == _MODE_INNER:
            if classname == 'caksound':
                allow = cfg.default_allow
            else:
                allow = True
        else:
            allow = cfg.default_allow


        for filter in cfg.filters:
            if filter.match(sid, hashname, classname, bankname, index):
                allow = not filter.excluded

        return allow

    # Checks if an outer object should be generated, depending on outer filters.
    def allow_outer(self, node, nsid=None, hashname=None, classname=None, bankname=None, index=None):
        return self._allow(_MODE_OUTER, node, nsid, hashname, classname, bankname, index)

    # Same, the difference between inner/outer being, if filter is 123456789 (outer) it should generate
    # only that ID *and* generate any sub-nodes inside (inner). While if filter @/123456789 it
    # should exclude sub-nodes with that ID.
    def allow_inner(self, node, nsid=None, hashname=None, classname=None, bankname=None, index=None, bnode=None):
        return self._allow(_MODE_INNER, node, nsid, hashname, classname, bankname, index, bnode)

    # Same for unused. When filtering regular nodes, any others become "unused", so they are excluded by
    # default. You can include them back here.
    def allow_unused(self, node, nsid=None, hashname=None, classname=None, bankname=None, index=None):
        return self.generate_rest or self._allow(_MODE_UNUSED, node, nsid, hashname, classname, bankname, index)

    def _has_mode(self, mode):
        return bool(self._cfgs[mode].filters)

    def has_unused(self):
        return self._has_mode(_MODE_UNUSED)
