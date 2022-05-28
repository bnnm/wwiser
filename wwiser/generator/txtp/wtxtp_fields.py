# Info fields that get printed in the .txtp

# meh... (make one TxtpField per type? sorting?)
_FIELD_TYPE_PROP = 1
_FIELD_TYPE_KEYVAL = 2
_FIELD_TYPE_KEYMINMAX = 3
_FIELD_TYPE_RTPC = 4
_FIELD_TYPE_SC = 5


class _TxtpField(object):
    def __init__(self, type, items):
        self.type = type
        self.items = items

    # magical crap for sorting
    def __lt__(self, other):
        if self.type != other.type:
            return self.type < other.type

        if self.type == _FIELD_TYPE_SC:
            nkey1, nval1, _ = self.items
            nkey2, nval2, _ = other.items

            eq = self._equals(nkey1, nkey2)
            if eq is not None:
                return eq is True
            # on tie break with value
            return self._compare(nval1, nval2)

        if self.type == _FIELD_TYPE_RTPC:
            nfield1, _, _, _ = self.items
            nfield2, _, _, _ = other.items
            return self._compare(nfield1, nfield2)

        return False

    def _compare(self, nfield1, nfield2):
        eq = self._equals(nfield1, nfield2)
        return eq is True

    # <: True, =: None, >: False
    def _equals(self, nfield1, nfield2):
        name1, value1 = self._namevalue(nfield1)
        name2, value2 = self._namevalue(nfield2)

        if name1 and name2:
            if name1 == name2:
                return None
            return name1 < name2
        if name1:
            return True
        if name2:
            return False
        if value1 == value2:
            return None
        return value1 < value2

    def _namevalue(self, nfield):
        attrs = nfield.get_attrs()
       
        name = attrs.get('hashname')
        val = attrs.get('value')
        return (name, val)

class TxtpFields(object):
    def __init__(self):
        self._fields = []
        self._done = {}

    
    def _add(self, type, items, testkey=None):
        if not type or not items:
            return
        if testkey:
            done = (type, ) + testkey
            if done in self._done:
                return
            self._done[done] = True

        field = _TxtpField(type, items)
        self._fields.append(field)

    def _add2(self, key, testkey):
        done = (key[0], ) + testkey
        if done in self._done:
            return
        self._done[done] = True
        self._fields.append(key)

    def prop(self, nkey):
        if nkey:
            self._add(_FIELD_TYPE_PROP, (nkey))

    def props(self, nkeys):
        for nkey in nkeys:
            self.prop(nkey)

    def keyval(self, nkey, nval):
        if nkey and nval:
            self._add(_FIELD_TYPE_KEYVAL, (nkey, nval))

    def keyvals(self, nitems):
        for nitem in nitems:
            self.keyval(*nitem)

    def keyminmax(self, nkey, nmin, nmax):
        if nkey and nmin and nmax:
            self._add(_FIELD_TYPE_KEYMINMAX, (nkey, nmin, nmax))

    def keyminmaxs(self, nitems):
        for nitem in nitems:
            self.keyminmax(*nitem)

    def statechunk(self, nkey, nval, props):
        if nkey and nval:
            self._add(_FIELD_TYPE_SC, (nkey, nval, props), (nkey.value(), nval.value(), props.values()))

    def rtpc(self, nrtpc, nparam, values_x, values_y):
        if nrtpc and nparam:
            self._add(_FIELD_TYPE_RTPC, (nrtpc, nparam, values_x, values_y), (nrtpc.value(), nparam.value(), values_x, values_y))

    def sort(self):
        self._fields.sort()

    def _prop_info(self, nfield):
        attrs = nfield.get_attrs()

        key = attrs.get('name')
        val = attrs.get('valuefmt', attrs.get('hashname'))
        if not val:
            val = attrs.get('value')
        return key, val

    def _prop_name(self, nfld):
        fmt = nfld.get_attrs().get('valuefmt')
        if not fmt:
            return None
        try:
            index = fmt.index('[')
            fmt = fmt[index:]
        except ValueError:
            pass

        return fmt

    def generate(self):
        lines = []

        for field in self._fields:
            if not field:
                continue
                #raise ValueError("empty field (old version?)")
            type = field.type
            items = field.items

            if   type == _FIELD_TYPE_PROP:
                nfield = items
                key, val =  self._prop_info(nfield)

            elif type == _FIELD_TYPE_KEYVAL:
                nkey, nval = items

                key = self._prop_name(nkey)
                if not key:
                    kattrs = nkey.get_attrs()

                    kname = kattrs.get('name')
                    kvalue = kattrs.get('valuefmt', kattrs.get('hashname'))
                    if not kvalue:
                        kvalue = kattrs.get('value')
                    if not kvalue:
                        key = "%s" % (kname)
                    else:
                        key = "%s %s" % (kname, kvalue)

                vattrs = nval.get_attrs()
                val = vattrs.get('valuefmt', vattrs.get('hashname'))
                if not val:
                    val = vattrs.get('value')

            elif type == _FIELD_TYPE_KEYMINMAX:
                nkey, nmin, nmax = items
                kattrs = nkey.get_attrs()
                minattrs = nmin.get_attrs()
                maxattrs = nmax.get_attrs()

                key = "%s %s" % (kattrs.get('name'), kattrs.get('valuefmt', kattrs.get('value')))
                val = "(%s, %s)" % (minattrs.get('valuefmt', minattrs.get('value')), maxattrs.get('valuefmt', maxattrs.get('value')))

            elif type == _FIELD_TYPE_SC:
                nkey, nval, props = items
                kattrs = nkey.get_attrs() #nstategroupid
                vattrs = nval.get_attrs() #nstatevalueid

                kname = kattrs.get('name') #field's name
                kvalue = kattrs.get('hashname', kattrs.get('value')) #statechunk's group name/id
                vvalue = vattrs.get('hashname', vattrs.get('value')) #statechunk's value name/id

                info = ''
                if True:
                    for nfield in props.fields_fld:
                        pkey, pval = self._prop_info(nparam)
                        info += ", %s: %s" % (pkey, pval)

                    for nkey, nval in props.fields_std:
                        pk = self._prop_name(nkey)
                        pv = nval.value()
                        info += ", %s: %s" % (pk, pv)
                    
                    for nkey, nmin, nmax in props.fields_rng:
                        pk = self._prop_name(nkey)
                        pv1 = nmin.value()
                        pv2 = nmax.value()
                        info += ", %s: (%s,%s)" % (pk, pv1, pv2)
                    if info:
                        info = info[2:]

                key = "%s" % (kname)
                val = "(%s=%s)" % (kvalue, vvalue)
                if info:
                    val += " <%s>" % (info) #looks a bit strange though

            elif   type == _FIELD_TYPE_RTPC:
                nfield, nparam, values_x, values_y = items
                attrs = nfield.get_attrs()

                key = attrs.get('name')
                val = attrs.get('hashname', attrs.get('value'))
                if not val:
                    val = str(attrs.get('value'))

                min_x, default_x, max_x = values_x
                val = "{%s=%s,%s}" % (val, min_x, max_x)

                if nparam:
                    pfmt = self._prop_name(nparam)

                    min_y, default_y, max_y = values_y
                    val += " <%s: %s,%s>" % (pfmt, min_y, max_y)

                    if default_x is not None:
                        val += " (default %s: %s)" % (default_x, default_y)
                    #pkey, pval = self._prop_info(nparam)
                    #val += " <%s>" % (pkey, pval)

            else:
                raise ValueError("bad field")

            lines.append("* %s: %s" % (key, val))

        return lines
