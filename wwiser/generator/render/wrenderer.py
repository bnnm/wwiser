from . import wrenderer_util
from ..txtp import hnode_misc, wtxtp


class Renderer(object):
    def __init__(self, txtpcache, builder, wwstate, filter):
        self._txtpcache = txtpcache
        self._builder = builder
        self._filter = filter
        self._ws = wwstate

        # internals
        self._node = None
        self._ncaller = None
        self._bstinger = None
        self._btransition = None

    def get_generated_hircs(self):
        return wrenderer_util.GENERATED_BASE_HIRCS

    #------------------------------------

    # RENDER CHAINS:
    # Per each link, will try to find all possible combos. If there are combos,
    # we re-render again with each one for that link (which in turn may find combos for next link(s).
    # If no combo exists we skip to the next step (it's possible it didn't find GS combos but did SC combos).
    # 
    # example:
    # has GS combos bgm=m01/m02, SC combos layer=hi/lo, GV combos rank=N.N
    # - base (gets combos)
    #   - GS combo bgm=m01
    #     - SC combo layer=hi
    #       - GV combo rank=N.N
    #         - final txtp: "play_bgm (bgm=m01) {s}=(layer=hi) {rank=N.n}"
    #     - SC combo layer=lo
    #       - GV combo rank=N.N
    #         - final txtp: "play_bgm (bgm=m01) {s}=(layer=lo) {rank=N.n}"
    #   - GS combo bgm=m02
    #     - SC combo layer=hi
    #       - GV combo rank=N.N
    #         - final txtp: "play_bgm (bgm=m02) {s}=(layer=hi) {rank=N.n}"
    #     - SC combo layer=lo
    #       - GV combo rank=N.N
    #         - final txtp: "play_bgm (bgm=m02) {s}=(layer=lo) {rank=N.n}"
    #
    # base: no GS combos bgm=m01/m02, no SC combos, GV combos rank=N.N
    # - base (gets combos)
    #   - GS: none, skip
    #     - SC: none, skip
    #       - GV combo rank=N.n
    #         - final txtp: "play_bgm {rank=N.n}"
    #
    # It's possible to set defaults with CLI/GUI, in which case combos/params are fixed to certain values
    # and won't fill them during process or try multi-combos (outside those defined in config).
    # 
    # defaults: GS bgm=m01, SC layer=hi, GV rank=N.n
    # - base (gets combos)
    #   - GS combo bgm=m01
    #     - SC combo layer=hi
    #       - GV combo rank=N.N
    #         - final txtp: "play_bgm (bgm=m01) {s}=(layer=hi) {rank=N.n}"
    #
    # On each combo we need to reset next link's combos, as they may depend on previous config.
    # For example, by default it may find GS bgm=m01/m02, SC layer=hi/mid/lo (all possible combos of everything),
    # but actually GS bgm=m01 has SC layer=hi/mid and GS bgm=m02 has SC layer=mid/lo (would create fake dupes if
    # we just try all possible SCs every time).


    # handle new txtp with default parameters
    def render_node(self, node):
        ncaller = node.find1(type='sid')

        self._render_node(node)
        self._render_subs(ncaller)


    # initial render. if there are no combos this will be passed until final step
    def _render_node(self, node):
        self._set_node(node) #no caller
        self._ws.reset() # each new node starts from 0

        txtp = self._make_txtp()
        self._render_gs(txtp)

    # derived render, depending on sub-nodes
    def _render_subs(self, ncaller):
        # get values before resetting
        ws = self._ws
        bstingers = ws.stingers.get_items()
        btransitions = ws.transitions.get_items()

        # stingers found during process
        if bstingers:
            for bstinger in bstingers:
                self._ws.reset()
                self._set_stinger(ncaller, bstinger)

                txtp = self._make_txtp()
                #self._render_last(txtp)
                self._render_gs(txtp)

        # transitions found during process
        if btransitions:
            for btransition in btransitions:
                self._ws.reset()
                self._set_transition(ncaller, btransition)

                txtp = self._make_txtp()
                #self._render_last(txtp)
                self._render_gs(txtp)

        # transition (stingers too probably) segments may also not exist (seen in Detroit)

    #-------------------------------------

    # handle combinations of gamesyncs: "play_bgm (bgm=m01)", "play_bgm (bgm=m02)", ...
    def _render_gs(self, txtp):
        ws = self._ws

        # SCs have regular states and "unreachable" ones. If we have GS bgm=m01 and SC bgm=m01/m02,
        # m02 is technically not reachable (since GS states and SC states are the same thing).
        # Sometimes they are interesting so we want them, but *after* all regular SCs to skip dupes.
        unreachables = []

        gscombos = ws.get_gscombos()
        if not gscombos:
            # no combo to re-render, skips to next step
            self._render_sc(txtp)

        else:
            # re-render with each combo
            for gscombo in gscombos:
                ws.set_gs(gscombo)
                ws.reset_sc()
                ws.reset_gv()

                txtp = self._make_txtp()
                self._render_sc(txtp)

                if ws.scpaths.has_unreachables():
                    unreachables.append(gscombo)


            if not self._txtpcache.statechunks_skip_unreachables:
                for gscombo in unreachables:
                    ws.set_gs(gscombo)
                    ws.reset_sc()
                    ws.reset_gv()

                    txtp = self._make_txtp()
                    self._render_sc(txtp, make_unreachables=True)



    # handle combinations of statechunks: "play_bgm (bgm=m01) {s}=(bgm_layer=hi)", "play_bgm (bgm=m01) {s}=(bgm_layer=lo)", ...
    def _render_sc(self, txtp, make_unreachables=False):
        ws = self._ws

        #TODO simplify: set scpaths to reachable/unreachable modes (no need to check sccombo_hash unreachables)
        ws.scpaths.filter(ws.gsparams) #detect unreachables

        sccombos = ws.get_sccombos() #found during process
        if not sccombos:
            # no combo to re-render, skips to next step
            self._render_gv(txtp)

        else:
            # re-render with each combo
            for sccombo in sccombos:
                if not make_unreachables and sccombo.has_unreachables(): #not ws.scpaths.is_unreachables_only():
                    continue
                if make_unreachables and not sccombo.has_unreachables(): #ws.scpaths.is_unreachables_only():
                    continue

                ws.set_sc(sccombo)
                ws.reset_gv()

                txtp = self._make_txtp()
                self._render_gv(txtp)


            # needs a base .txtp in some cases
            if not self._txtpcache.statechunks_skip_default and not make_unreachables and ws.scpaths.generate_default(sccombos):
                ws.set_sc(None)
                ws.reset_gv()

                txtp = self._make_txtp(scdefs=True)
                self._render_gv(txtp)


    # handle combinations of gamevars: "play_bgm (bgm=m01) {s}=(bgm_layer=hi) {bgm_rank=2.0}"
    def _render_gv(self, txtp):
        ws = self._ws

        gvcombos = ws.get_gvcombos()
        if not gvcombos:
            # no combo to re-render, skips to next step
            self._render_last(txtp)

        else:
            # re-render with each combo
            for gvcombo in gvcombos:
                ws.set_gv(gvcombo)

                txtp = self._make_txtp()
                self._render_last(txtp)


    # final chain link
    def _render_last(self, txtp):
        txtp.write()

    #-------------------------------------

    def _begin_txtp(self, txtp):
        node = self._node

        bnode = self._builder._init_bnode(node)
        if not bnode:
            return

        root_config = hnode_misc.NodeConfig() #empty
        txtp.begin(node, root_config)

        rnode = self._get_rnode(bnode)
        rnode._render_base(bnode, txtp)

        return

    def _make_txtp(self, scdefs=False):
        txtp = wtxtp.Txtp(self._txtpcache)

        txtp.scparams_make_default = scdefs
        txtp.set_ncaller(self._ncaller)
        txtp.set_bstinger(self._bstinger)
        txtp.set_btransition(self._btransition)

        self._begin_txtp(txtp)

        return txtp

    def _set_items(self, node, ncaller=None, bstinger=None, btransition=None):
        self._node = node
        self._ncaller = ncaller
        self._bstinger = bstinger
        self._btransition = btransition

    def _set_node(self, node):
        self._set_items(node)

    def _set_stinger(self, ncaller, bstinger):
        node = self._builder._get_node_link(bstinger.ntid)
        self._set_items(node, ncaller=ncaller, bstinger=bstinger)

    def _set_transition(self, ncaller, btransition):
        node = self._builder._get_node_link(btransition.ntid)
        self._set_items(node, ncaller=ncaller, btransition=btransition)

    #-------------------------------------

    def _get_rnode(self, bnode):
        if not bnode:
            return None

        # check is node already in cache
        #rnode = self._node_to_bnode.get(id(node))
        #if rnode:
        #    return rnode

        # render node with a helper class and save to cache
        # (some banks get huge and call the same things again and again, it gets quite slow to parse every time)
        hircname = bnode.node.get_name()
        rclass = wrenderer_util.get_renderer_hirc(hircname)

        rnode = rclass()
        rnode.init_renderer(self)

        #self._node_to_bnode[id(node)] = rnode
        return rnode
