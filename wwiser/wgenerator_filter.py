import fnmatch


class GeneratorFilterItem(object):
    def __init__(self, value):
        # whether when node matches this filter node is included or excluded
        self.excluded = False
        # whether node matches outer (base events) or inner (objects part of event)
        self.inner = False
        # filter must compare value vs a sid/bank/class. 
        self.use_sid = False
        self.use_bank = False
        self.use_class = False
        # if value matches a pattern
        self.is_pattern = False
        # actual filter
        self.value = None

        value = value.lower()
        if value.startswith('@'):
            self.inner = True
            value = value[1:]

        if value.startswith('-') or value.startswith('/') :
            self.excluded = True
            value = value[1:]

        self.value = value
        
        if '*' in value:
            self.is_pattern = True

        if value.isnumeric():
            self.use_sid = True
        elif value.startswith('cak'):
            self.use_class = True
        elif value.endswith('.bnk'):
            self.use_bank = True
        else:
            pass

        return

    def match(self, sid, hashname, classname, bankname):
        if   self.use_sid:
            comps = [str(sid)]
        elif self.use_bank:
            comps = [bankname]
        elif self.use_class:
            comps = [classname]
        else:
            comps = [str(sid), hashname] #, classname, bankname # bnk  and hashnames sometimes clash

        for comp in comps:
            if not comp:
                continue
            comp = comp.lower()
            if self.is_pattern and fnmatch.fnmatch(comp, self.value):
                return True
            elif comp == self.value:
                return True

        return False
    
class GeneratorFilterConfig(object):
    def __init__(self, inner, filters):
        self.inner = inner
        self.generate_all = False
        self.default_generate = False
        self.filters = []
        self.valid_hircs = []
        self._load(filters)

    def _load(self, filters):
        has_includes = False
        has_all = False
        for filter in filters:
            if self.inner and not filter.inner:
                continue
            if not self.inner and filter.inner:
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
            self.default_generate = False
        else:
            self.default_generate = True

        # for outer nodes, by default only Event types are generated (generate_all is false).
        # for inner nodes, by default all objects are generated (generate_all is true).
        if self.inner:
            self.generate_all = True
        else:
            self.generate_all = False

        # filtering by class or id means generating all
        if has_all:
            self.generate_all = True

        return

class GeneratorFilter(object):
    def __init__(self):
        self.active = False
        self._default_hircs = []
        self._inner_cfg = None
        self._outer_cfg = None
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
            gfi = GeneratorFilterItem(item)
            filters.append(gfi)

        self._outer_cfg = GeneratorFilterConfig(False, filters)
        self._inner_cfg = GeneratorFilterConfig(True, filters)
        return

    def _generate(self, inner, node, nsid=None, hashname=None, classname=None, bankname=None):
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

        if inner:
            cfg = self._inner_cfg
        else:
            cfg = self._outer_cfg

        if not cfg.generate_all and classname not in self._default_hircs:
            return False

        generate = cfg.default_generate
        for filter in cfg.filters:
            if filter.match(sid, hashname, classname, bankname):
                generate = not filter.excluded

        return generate

    # Checks if an outer object should be generated, depending on outer filters.
    def generate_outer(self, node, nsid=None, hashname=None, classname=None, bankname=None):
        return self._generate(False, node, nsid, hashname, classname, bankname)

    # Checks if an inner object should be generated, depending on inner filters.
    # The difference between inner/outer being, if filter is 123456789 (outer) it should generate
    # only that ID *and* generate all sub-nodes inside (inner). While if filter >123456789 it
    # should generate any ID *and* generate only sub-nodes with that ID.
    def generate_inner(self, node, nsid=None, hashname=None, classname=None, bankname=None):
        return self._generate(True, node, nsid, hashname, classname, bankname)
