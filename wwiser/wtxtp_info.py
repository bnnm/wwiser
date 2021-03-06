import logging, os
from . import wgamesync


class TxtpInfo(object):
    def __init__(self, wemnames=False):
        self._depth = 0
        self._ninfo = []
        self._banks = None
        self._wemnames = ''
        self._gsnames = ''
        self._set_wemnames = wemnames
        pass

    def get_gsnames(self):
        return self._gsnames

    def get_wemnames(self):
        return self._wemnames

    def get_lines(self):
        if self._banks is None:
            self.get_banks()

        is_multibank = len(self._banks) > 1

        lines = []
        for ninfo in self._ninfo:
            info = ninfo.generate(is_multibank)
            lines.append(info)
        return lines

    def get_banks(self):
        banks = []
        for ninfo in self._ninfo:
            node = ninfo.get_node()
            if node:
                bank = node.get_root().get_filename()
                if bank not in banks:
                    banks.append(bank)
        self._banks = banks
        return banks

    def source(self, ntid, source):
        nfields = None
        if source:
            nfields = [source.nplugin]

        next = TxtpInfoNode(self._depth + 1, None, nfields, None, source=ntid)
        self._ninfo.append(next)

        if self._set_wemnames:
            attrs = ntid.get_attrs()
            wemname = attrs.get('guidname', attrs.get('path'))
            if wemname:
                basename = os.path.basename(wemname) #[:-4]
                basename = os.path.splitext(basename)[0]
                basename = basename.strip()
                finalname = "{%s}" % (basename)
                if finalname not in self._wemnames:
                    self._wemnames += ' ' + finalname

    def next(self, node, nfields, nattrs=None, nsid=None):
        self._depth += 1

        next = TxtpInfoNode(self._depth, node, nfields, nattrs, nsid=nsid)
        self._ninfo.append(next)

    def done(self):
        self._depth -= 1

    def gamesync(self, gtype, ngname, ngvalue):
        self.gamesyncs([(gtype, ngname, ngvalue)])

    def gamesyncs(self, gamesyncs):
        current = self._ninfo[-1]

        current.add_gamesyncs(gamesyncs)
        info = current.get_gamesync_text()

        self._gsnames += " " + info


class TxtpInfoNode(object):
    OBJECT_NAMES = ['hashname', 'guidname', 'path', 'objpath']

    def __init__(self, depth, node, nfields, nattrs, nsid=None, source=None):
        self.depth = depth
        self.node = node
        self.nsid = nsid
        self.nfields = nfields
        self.nattrs = nattrs
        self.gamesync = '' #text
        self.source = source
        self._info = None

    def add_gamesyncs(self, gamesyncs):
        if self.gamesync:
            raise ValueError("multiple gamesyncs in same info node")

        info = ''
        for gtype, ngname, ngvalue in gamesyncs:

            name = ngname.get_attrs().get('hashname')
            if not name:
                name = ngname.value()
            value = ngvalue.get_attrs().get('hashname')
            if not value:
                value = ngvalue.value()
            if value == 0:
                value = '-'

            if   gtype == wgamesync.TYPE_STATE:
                type = "(%s=%s)" % (name, value) # states = more globals = "("
            elif gtype == wgamesync.TYPE_SWITCH:
                type = "[%s=%s]" % (name, value) # switches = more restrictive = "["
            else:
                raise ValueError("unknown gamesync type %i" % (gtype))

            info += type

        self.gamesync = info

    def get_gamesync_text(self):
        return self.gamesync

    def get_node(self):
        return self.node

    def generate(self, multibank=False):
        self.padding = ' ' * (self.depth * 2 + 1) #+1 for '# ' space after comment
        self._info = []

        self._generate_node(multibank)
        self._generate_gamesync()
        self._generate_source()
        self._generate_fields()

        self._info.append('#\n')
        return ''.join(self._info)

    def _generate_node(self, multibank):
        node = self.node
        if not node:
            return
        index = node.get_attr('index')

        nsid = self.nsid
        if not nsid:
            nsid = node.find1(type='sid')

        line = ''
        # base node
        line += node.get_name()
        if index is not None:
            line += '[%s]' % (index)
        if nsid:
            line += ' %i' % (nsid.value())

        if multibank:
            line += ' / %s' % (node.get_root().get_filename())

        self._info.append( '#%s%s\n' % (self.padding, line) )

        # node names
        if nsid:
            attrs = nsid.get_attrs() #base object > sid + names
        else:
            attrs = node.get_attrs() #regular node with names

        for key, val in attrs.items():
            if not key in self.OBJECT_NAMES:
                continue
            self._info.append( '#%s- %s: %s\n' % (self.padding, key, val) )

    def _generate_fields(self):
        if not self.nfields:
            return
        for nfield in self.nfields:
            if not nfield:
                continue
                #raise ValueError("empty field (old version?)")

            if isinstance(nfield, tuple):
                if   len(nfield) == 2:
                    nkey, nval = nfield
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

                elif len(nfield) == 3:
                    nkey, nmin, nmax = nfield
                    kattrs = nkey.get_attrs()
                    minattrs = nmin.get_attrs()
                    maxattrs = nmax.get_attrs()
                    key = "%s %s" % (kattrs.get('name'), kattrs.get('valuefmt', kattrs.get('value')))
                    val = "(%s, %s)" % (minattrs.get('valuefmt', minattrs.get('value')), maxattrs.get('valuefmt', maxattrs.get('value')))

                else:
                    raise ValueError("bad tuple")
            else:
                attrs = nfield.get_attrs()
                key = attrs.get('name')
                val = attrs.get('valuefmt', attrs.get('hashname'))
                if not val:
                    val = attrs.get('value')

            self._info.append( '#%s* %s: %s\n' % (self.padding, key, val) )

    def _generate_gamesync(self):
        if not self.gamesync:
            return
        self._info.append( '#%s~ %s\n' % (self.padding, self.gamesync) )

    def _generate_source(self):
        ntid = self.source
        if not ntid:
            return

        attrs = ntid.get_attrs()
        names = set(['hashname', 'guidname', 'path', 'objpath'])

        name = 'Source'
        sid = ntid.value()

        self._info.append( '#%s%s %i\n' % (self.padding, name, sid) )
        for key, val in attrs.items():
            if not key in names:
                continue
            self._info.append( '#%s- %s: %s\n' % (self.padding, key, val) )
