import os
from . import wtxtp_fields
from ..registry import wgamesync

###
# saves a printable info tree


class TxtpInfo(object):
    def __init__(self, txtpcache):
        self._depth = 0
        self._ninfo = []
        self._banks = None
        self._wemnames = ''

        self._rtpc_fields = wtxtp_fields.TxtpFields()
        self._statechunk_fields = wtxtp_fields.TxtpFields()

        self._gsnames_init = False
        self._gsnames_idx = []
        self._gsnames_long = ''
        self._gsnames_short = ''

        self._gvnames_init = False
        self._gvitems = []
        self._gvdone = set()
        self._gvnames = ''

        self._scnames_init = False
        self._scitems = []
        self._scdone = set()
        self._scnames = ''

        self._txtpcache = txtpcache
        pass

    def _print_tree(self):
        print("node")
        for i, ninfo in enumerate(self._ninfo):
            text = ninfo.gstext_long
            if not text:
                text = bool(ninfo.source)
            print(' '* ninfo.depth, "ninfo", i, ":", text)
        print("gs",self._gsnames_idx)


    # set next node
    def next(self, node, fields, nsid=None):
        self._depth += 1

        inext = TxtpInfoNode(self._depth, node, fields, nsid=nsid)
        self._ninfo.append(inext)

    def done(self):
        self._depth -= 1


    # Typically gamesyncs can be written one after another, but rarely some may not
    # lead to anything playable, thus useless in final name so we want them out.
    # Because the "tree" is just a simple array with depths, use some indexes to quickly
    # find gamesyncs and closest sources, that should tell us if that should be dropped
    # Faster than reading a proper tree but more much complex:
    #   node 0
    #     node1 : PLAYER=ALIVE
    #       node2 : BGM=01
    #         node3 : source
    #     node4 : MODE=GAMEPLAY *dropped
    #     node5 : 
    #       node6 : MODE=MENU
    #         node7 : source
    #     node8 : MODE=GAMEPLAY *dropped
    # 
    # Final vars: "(PLAYER=ALIVE) (BGM=01) (MODE=MENU)"
    # GS idxs: [1, 2, 4, 6, 8]
    # - node1: has lower source 3
    # - node2: has lower source 3
    # - node4: no lower source = dropped (next is node7 but node5's depth is >= than node4)
    # - node6: has lower source 7
    # - node8: no lower source = dropped (no more nodes of lower depth)
    #
    # There is a lot of FORs needed to find sources, but a long event may have ~10 GSs and
    # a short one ~2, so it shouldn't be that slow on average

    # register gamesync for current node
    def gamesync(self, gtype, ngname, ngvalue):
        self.gamesyncs([(gtype, ngname, ngvalue)])

    def gamesyncs(self, gamesyncs):
        current = self._ninfo[-1]

        current.add_gamesyncs_info(gamesyncs, self._txtpcache.name_vars)

        if current.gstext_long or current.gstext_short:
            self._gsnames_idx.append(len(self._ninfo) - 1)

    def get_gsnames(self, long=False):
        if not self._gsnames_init:
            self._load_gsnames()

        if long:
            return self._gsnames_long
        return self._gsnames_short

    def _load_gsnames(self):
        self._gsnames_init = True
        for gs_idx in self._gsnames_idx:
            current = self._ninfo[gs_idx]
            if not self._has_source(gs_idx):
                continue

            if current.gstext_long:
                self._gsnames_long += " " + current.gstext_long
            if current.gstext_short:
                self._gsnames_short += " " + current.gstext_short

    def _has_source(self, gs_idx):
        current = self._ninfo[gs_idx]
        for i in range(gs_idx + 1, len(self._ninfo)):
            next = self._ninfo[i]

            # lower nodes only
            if next.depth <= current.depth:
                break
            if next.source:
                return True

        return False

    # Gamevars (RTPC ID+values) are only interesting when used, and usage may depend on current set GVs
    # and if any node or its parent uses them. So instead of finding them in the tree, useds GVs are registered.

    # register gamesync for current node, but only once since one gamevar may apply to many nodes
    def gamevar(self, ngvname, value):
        self.gamevars([(ngvname, value)])

    def gamevars(self, gamevars):
        for gamevar in gamevars:
            gvname = gamevar[0].value()
            if gvname in self._gvdone:
                continue
            self._gvdone.add(gvname)
            self._gvitems.append(gamevar)

    def get_gvnames(self):
        if not self._gvnames_init:
            self._load_gvnames()
        return self._gvnames

    def _load_gvnames(self):
        self._gvnames_init = True
        for ngvname, value in self._gvitems:
            name = ngvname.get_attrs().get('hashname')
            if not name:
                name = ngvname.value()

            info = "{%s=%s}" % (name, value)
            self._gvnames += info

    # statechunks, same as gamevars (register when used)
    def statechunk(self, state):
        self.statechunks([(state)])

    def statechunks(self, states):
        for state in states:
            key = (state.group, state.value) #probably key only is ok, leave both to detect logic bugs
            if key in self._scdone:
                continue
            self._scdone.add(key)
            self._scitems.append(state)

    def get_scnames(self):
        if not self._scnames_init:
            self._load_scnames()
        return self._scnames

    def _load_scnames(self):
        self._scnames_init = True
        has_unreachables = False
        for state in self._scitems:
            name = state.group_name
            if not name:
                name = state.group
            value = state.value_name
            if not value:
                value = state.value

            info = "{%s=%s}" % (name, value)
            if state.unreachable:
                has_unreachables = True
            self._scnames += info

        # extra mark
        if has_unreachables:
            self._scnames = '~' + self._scnames

    #----------------------------------------------------------------------------------

    # other registered info found during process
    def get_wemnames(self):
        return self._wemnames

    def get_tree_lines(self):
        if self._banks is None:
            self.get_banks()

        is_multibank = len(self._banks) > 1

        lines = ["# PATH\n"]
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
        fields = wtxtp_fields.TxtpFields()
        if source:
            fields.prop(source.nplugin)

        inext = TxtpInfoNode(self._depth + 1, None, fields, None, source=ntid)
        self._ninfo.append(inext)

        if self._txtpcache.name_wems:
            attrs = ntid.get_attrs()
            wemname = attrs.get('guidname', attrs.get('path'))
            if wemname:
                basename = os.path.basename(wemname) #[:-4]
                basename = os.path.splitext(basename)[0]
                basename = basename.strip()
                finalname = "{%s}" % (basename)
                if finalname not in self._wemnames:
                    self._wemnames += ' ' + finalname


    def _get_fields_lines(self, info, fields):
        lines = fields.generate()
        if not lines:
            return None

        out_lines = ["# %s\n" % (info)]
        for line in lines:
            out_lines.append( '#%s%s\n' % (" ", line) )
        return out_lines

    def report_rtpc(self, brtpc):
        self._rtpc_fields.rtpc(brtpc.nid, brtpc.minmax(), brtpc.nparam)

    def get_gamevar_lines(self):
        return self._get_fields_lines("GAMEVARS", self._rtpc_fields)

    def report_statechunk(self, bsi):
        self._statechunk_fields.statechunk(bsi.nstategroupid, bsi.nstatevalueid, bsi.bstate.props)

    def get_statechunk_lines(self):
        return self._get_fields_lines("STATECHUNKS", self._statechunk_fields)


#class NameInfo(object):
#    def __init__(self, ntid=None):
#
#        self.id = None
#        self.name = None
#        if not ntid:
#            return
#
#        self.id = ntid.value()
#        attrs = ntid.get_attrs()
#        self.name = attrs.get('hashname')

class TxtpInfoNode(object):
    OBJECT_NAMES = ['hashname', 'guidname', 'path', 'objpath']

    def __init__(self, depth, node, fields, nsid=None, source=None):
        self.depth = depth
        self.node = node
        self.nsid = nsid
        self.fields = fields
        self.gstext_long = ''
        self.gstext_short = ''
        self.source = source
        self._info = None

    def add_gamesyncs_info(self, gamesyncs, name_vars):
        if self.gstext_long or self.gstext_short:
            raise ValueError("multiple gamesyncs in same info node")

        info_long = ''
        info_short = ''
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

            # By default ignore variables like (thing=-) since they tend to get wordy and don't give much info
            # some cases may look better with them ("play_bgm [music=-]" + play_bgm [music=bgm1] + ..., by default first would be "play_bgm")
            # Only for "short" version of text info, that is used as name (standard version is written inside txtp)
            if not name_vars and value == '-':
                pass
            else:
                info_short += type
            info_long += type

        self.gstext_long = info_long
        self.gstext_short = info_short

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
        if not self.fields:
            return

        lines = self.fields.generate()
        for line in lines:
            self._info.append( '#%s%s\n' % (self.padding, line) )

    def _generate_gamesync(self):
        if not self.gstext_long:
            return
        self._info.append( '#%s~ %s\n' % (self.padding, self.gstext_long) )

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
