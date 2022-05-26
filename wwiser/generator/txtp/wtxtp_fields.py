# Info fields that get printed in the .txtp

# meh...
FIELD_TYPE_PROP = 0
FIELD_TYPE_KEYVAL = 1
FIELD_TYPE_KEYMINMAX = 2
FIELD_TYPE_RTPC = 3
FIELD_TYPE_SC = 4

class TxtpFields(object):
    def __init__(self):
        self._fields = []
        self._done = {}

    def _add(self, key, testkey):
        done = (key[0], ) + testkey
        if done in self._done:
            return
        self._done[done] = True
        self._fields.append(key)

    def prop(self, nfield):
        if nfield:
            self._fields.append((FIELD_TYPE_PROP, nfield))

    def props(self, fields):
        for field in fields:
            self.prop(field)

    def keyval(self, nkey, nval):
        if nkey:
            self._fields.append((FIELD_TYPE_KEYVAL, nkey, nval))

    def statechunk(self, nkey, nval, props):
        if nkey:
            self._add((FIELD_TYPE_SC, nkey, nval, props), (nkey.value(), nval.value()))

    def keyminmax(self, nkey, nmin, nmax):
        if nkey:
            self._fields.append((FIELD_TYPE_KEYMINMAX, nkey, nmin, nmax))

    def rtpc(self, nrtpc, minmax, nparam):
        if nrtpc:
            self._add((FIELD_TYPE_RTPC, nrtpc, minmax, nparam), (nrtpc.value(), minmax, nparam.value()))

    def _info_prop(self, nfield):
        attrs = nfield.get_attrs()

        key = attrs.get('name')
        val = attrs.get('valuefmt', attrs.get('hashname'))
        if not val:
            val = attrs.get('value')
        return key, val

    def generate(self):
        lines = []

        for field in self._fields:
            if not field:
                continue
                #raise ValueError("empty field (old version?)")

            type = field[0]

            if   type == FIELD_TYPE_PROP:
                _, nfield = field
                key, val =  self._info_prop(nfield)

            elif type == FIELD_TYPE_KEYVAL:
                _, nkey, nval = field
                kattrs = nkey.get_attrs()
                vattrs = nval.get_attrs()

                kname = kattrs.get('name')
                kvalue = kattrs.get('valuefmt', kattrs.get('hashname'))
                if not kvalue:
                    kvalue = kattrs.get('value')

                if not kvalue:
                    key = "%s" % (kname)
                else:
                    key = "%s %s" % (kname, kvalue)

                val = vattrs.get('valuefmt', vattrs.get('hashname'))
                if not val:
                    val = vattrs.get('value')

            elif type == FIELD_TYPE_SC:
                _, nkey, nval, props = field
                kattrs = nkey.get_attrs() #nstategroupid
                vattrs = nval.get_attrs() #nstatevalueid

                kname = kattrs.get('name') #field's name
                kvalue = kattrs.get('hashname', kattrs.get('value')) #statechunk's group name/id
                vvalue = vattrs.get('hashname', vattrs.get('value')) #statechunk's value name/id

                info = ''
                if True:
                    for nkey, nval in props.fields_std:
                        pk = nkey.get_attrs().get('valuefmt')
                        pv = nval.value()
                        info += " %s=%s" % (pk, pv)
                    
                    for nkey, nmin, nmax in props.fields_rng:
                        pk = nkey.get_attrs().get('valuefmt')
                        pv1 = nmin.value()
                        pv2 = nmax.value()
                        info += " %s=(%s,%s)" % (pk, pv1, pv2)

                key = "%s" % (kname)
                val = "(%s=%s)" % (kvalue, vvalue)
                if info:
                    val += " {%s}" % (info.strip()) #looks a bit strange though

            elif type == FIELD_TYPE_KEYMINMAX:
                _, nkey, nmin, nmax = field
                kattrs = nkey.get_attrs()
                minattrs = nmin.get_attrs()
                maxattrs = nmax.get_attrs()

                key = "%s %s" % (kattrs.get('name'), kattrs.get('valuefmt', kattrs.get('value')))
                val = "(%s, %s)" % (minattrs.get('valuefmt', minattrs.get('value')), maxattrs.get('valuefmt', maxattrs.get('value')))

            elif   type == FIELD_TYPE_RTPC:
                _, nfield, minmax, nparam = field
                attrs = nfield.get_attrs()

                key = attrs.get('name')
                val = attrs.get('valuefmt', attrs.get('hashname'))
                if not val:
                    val = str(attrs.get('value'))
                min, max = minmax

                val = "{%s=%s,%s}" % (val, min, max)

                if nparam:
                    pkey, pval = self._info_prop(nparam)
                    val += " <%s: %s>" % (pkey, pval)

            else:
                raise ValueError("bad field")

            lines.append("* %s: %s" % (key, val))

        return lines
