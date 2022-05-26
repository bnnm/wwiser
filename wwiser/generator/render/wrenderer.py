from . import wrenderer_util
from ..txtp import hnode_misc, wtxtp


class Renderer(object):
    def __init__(self, txtpcache, builder, wwstate, filter):
        self._txtpcache = txtpcache
        self._builder = builder
        self._filter = filter
        self._ws = wwstate


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

        self._ws.reset() #each new node starts from 0

        # initial render. if there are no combos this will be passed until final step
        txtp = wtxtp.Txtp(self._txtpcache)
        self._begin_txtp(txtp, node)

        self._render_gs(node, txtp)

        self._render_subs(ncaller)


    # handle combinations of gamesyncs: "play_bgm (bgm=m01)", "play_bgm (bgm=m02)", ...
    def _render_gs(self, node, txtp):
        ws = self._ws

        # SCs have regular states and "unreachable" ones. If we have GS bgm=m01 and SC bgm=m01/m02,
        # m02 is technically not reachable (since GS states and SC states are the same thing).
        # Sometimes they are interesting so we want them, but *after* all regular SCs to skip dupes.
        unreachables = []

        gscombos = ws.get_gscombos()
        if not gscombos:
            # no combo to re-render, skips to next step
            self._render_sc(node, txtp)

        else:
            # re-render with each combo
            for gscombo in gscombos:
                ws.set_gs(gscombo)
                ws.reset_sc()
                ws.reset_gv()

                txtp = wtxtp.Txtp(self._txtpcache)
                self._begin_txtp(txtp, node)

                self._render_sc(node, txtp)

                if ws.scpaths.has_unreachables():
                    unreachables.append(gscombo)



            for gscombo in unreachables:
                ws.set_gs(gscombo)
                ws.reset_sc()
                ws.reset_gv()

                txtp = wtxtp.Txtp(self._txtpcache)
                self._begin_txtp(txtp, node)

                self._render_sc(node, txtp, make_unreachables=True)



    # handle combinations of statechunks: "play_bgm (bgm=m01) {s}=(bgm_layer=hi)", "play_bgm (bgm=m01) {s}=(bgm_layer=lo)", ...
    def _render_sc(self, node, txtp, make_unreachables=False):
        ws = self._ws

        #TODO simplify: set scpaths to reachable/unreachable modes (no need to check sccombo_hash unreachables)
        ws.scpaths.filter(ws.gsparams, self._txtpcache.wwnames) #detect unreachables

        sccombos = ws.get_sccombos() #found during process
        if not sccombos:
            # no combo to re-render, skips to next step
            self._render_gv(node, txtp)

        else:
            # re-render with each combo
            for sccombo in sccombos:
                if not make_unreachables and sccombo.has_unreachables(): #not ws.scpaths.is_unreachables_only():
                    continue
                if make_unreachables and not sccombo.has_unreachables(): #ws.scpaths.is_unreachables_only():
                    continue

                ws.set_sc(sccombo)
                ws.reset_gv()

                txtp = wtxtp.Txtp(self._txtpcache)
                self._begin_txtp(txtp, node)

                self._render_gv(node, txtp)


            # needs a base .txtp in some cases
            if not make_unreachables and ws.scpaths.generate_default(sccombos):
                ws.set_sc(None)
                ws.reset_gv()

                txtp = wtxtp.Txtp(self._txtpcache)
                txtp.scparams_make_default = True
                self._begin_txtp(txtp, node)

                self._render_gv(node, txtp)


    # handle combinations of gamevars: "play_bgm (bgm=m01) {s}=(bgm_layer=hi) {bgm_rank=2.0}"
    def _render_gv(self, node, txtp):
        ws = self._ws

        gvcombos = ws.get_gvcombos()
        if not gvcombos:
            # no combo to re-render, skips to next step
            self._render_last(node, txtp)

        else:
            # re-render with each combo
            for gvcombo in gvcombos:
                ws.set_gv(gvcombo)

                txtp = wtxtp.Txtp(self._txtpcache)
                self._begin_txtp(txtp, node)

                self._render_last(node, txtp)


    # final chain link
    def _render_last(self, node, txtp):
        txtp.write()


    def _render_subs(self, ncaller):
        ws = self._ws

        # stingers found during process
        bstingers = ws.stingers.get_items()
        if bstingers:
            for bstinger in bstingers:
                txtp = wtxtp.Txtp(self._txtpcache)
                self._begin_txtp_ntid(txtp, bstinger.ntid)
                txtp.set_ncaller(ncaller)
                txtp.set_bstinger(bstinger)
                txtp.write()

        # transitions found during process
        btransitions = ws.transitions.get_items()
        if btransitions:
            for btransition in btransitions:
                txtp = wtxtp.Txtp(self._txtpcache)
                self._begin_txtp_ntid(txtp, btransition.ntid)
                txtp.set_ncaller(ncaller)
                txtp.set_btransition(btransition)
                txtp.write()

    #-------------------------------------

    def _begin_txtp(self, txtp, node):
        bnode = self._builder._init_bnode(node)
        if not bnode:
            return

        root_config = hnode_misc.NodeConfig() #empty
        txtp.begin(node, root_config)

        rnode = self._get_rnode(bnode)
        rnode._render_base(bnode, txtp)

        return

    def _begin_txtp_ntid(self, txtp, ntid):
        node = self._builder._get_node_link(ntid)
        self._begin_txtp(txtp, node)

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
