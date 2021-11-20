import fnmatch, logging

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

        if '*' in value:
            self.is_pattern = True

        if value.isnumeric():
            # 123456789
            self.use_sid = True
        elif value.startswith('cak'):
            # CAk(type)
            self.use_class = True
        elif value.endswith('.bnk'):
            # (bankname).bnk
            self.use_bank = True
        elif '-' in value:
            # (bankname or bank hashname)-(index)-(description)
            self.use_index = True
            # ignore errors
            parts = value.split('-')
            self.value = parts[0] + '.bnk'
            self.value_index = int(parts[1])
        else:
            # event names
            pass

        return

    def match(self, sid, hashname, classname, bankname, index):

        value = self.value
        if   self.use_sid:
            comps = [str(sid)]
        elif self.use_bank:
            comps = [bankname]
        elif self.use_class:
            comps = [classname]
        elif self.use_index:
            # index needs multiple fields, check index here and bank below
            if self.value_index != index:
                return False
            comps = [bankname]
        else:
            comps = [str(sid), hashname] # bnk and hashnames sometimes clash

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
        self.allow_all = False
        self.default_allow = False
        self.filters = []
        self.valid_hircs = []
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

        # for outer nodes, by default only Event types are generated (allow_all is false).
        # for inner nodes, by default all objects are generated (allow_all is true).
        if self.mode in [_MODE_INNER, _MODE_UNUSED]:
            self.allow_all = True
        else:
            self.allow_all = False

        # filtering by class or id means generating all
        if has_all:
            self.allow_all = True

        return

class GeneratorFilter(object):
    def __init__(self):
        self.active = False
        self._default_hircs = []
        self._cfgs = {}
        self.rest = False # generate rest after filtering (rather than just filtered nodes)
        #self.transitions = False # filter transition objects
        #self.unused = False # filter transition objects

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

    def _allow(self, mode, node, nsid=None, hashname=None, classname=None, bankname=None, index=None):
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

        cfg = self._cfgs[mode]

        if not cfg.allow_all and classname not in self._default_hircs:
            return False

        allow = cfg.default_allow
        for filter in cfg.filters:
            if filter.match(sid, hashname, classname, bankname, index):
                allow = not filter.excluded

        return allow

    # Checks if an outer object should be generated, depending on outer filters.
    def allow_outer(self, node, nsid=None, hashname=None, classname=None, bankname=None, index=None):
        return self._allow(_MODE_OUTER, node, nsid, hashname, classname, bankname, index)

    # Checks if an inner object should be generated, depending on inner filters.
    # The difference between inner/outer being, if filter is 123456789 (outer) it should generate
    # only that ID *and* generate all sub-nodes inside (inner). While if filter >123456789 it
    # should generate any ID *and* generate only sub-nodes with that ID.
    def allow_inner(self, node, nsid=None, hashname=None, classname=None, bankname=None, index=None):
        return self._allow(_MODE_INNER, node, nsid, hashname, classname, bankname, index)
