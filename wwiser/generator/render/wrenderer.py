from . import wproperties
from . import wrenderer_util, bnode_misc, wstate


class Renderer(object):
    def __init__(self, builder, wwstate, filter):
        self._builder = builder
        self._filter = filter
        self._ws = wwstate
        self._calculator = wproperties.PropertyCalculator()

    def get_generated_hircs(self):
        return wrenderer_util.GENERATED_BASE_HIRCS


    def begin_txtp(self, txtp, node):
        bnode = self._builder._init_bnode(node)
        if not bnode:
            return

        #TODO remove
        txtp.gsparams = self._ws.gsparams
        #txtp.scpaths = self._ws.scpaths

        root_config = bnode_misc.NodeConfig() #empty
        txtp.begin(node, root_config)

        rnode = self._get_rnode(bnode)
        rnode._render_base(bnode, txtp)

        return

    def begin_txtp_ntid(self, txtp, ntid):
        node = self._builder._get_node_link(ntid)
        self.begin_txtp(txtp, node)

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
