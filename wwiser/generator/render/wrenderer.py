from . import wnode_misc
from . import wrenderer_util as ru


class Renderer(object):
    def __init__(self, builder, filter):
        self._builder = builder
        self._filter = filter

    def get_generated_hircs(self):
        return ru.GENERATED_BASE_HIRCS


    def begin_txtp(self, txtp, node):
        bnode = self._builder._get_bnode(node)
        if not bnode:
            return

        root_config = wnode_misc.NodeConfig()
        txtp.begin(node, root_config)

        rnode = self._get_rnode(bnode)
        rnode._render_base(bnode, txtp)

        return

    def begin_txtp_stinger(self, txtp, stinger):
        bnode = self._builder._get_bnode(stinger.node) #sid is stinger.ntrigger.value()
        if not bnode:
            return

        # not correct since CAkStinger have no sid (same TriggerID can call different segments),
        # this is to show info
        bnode.sid = stinger.ntrigger.value()
        bnode.nsid = stinger.ntrigger
        bnode.ntid = stinger.ntid

        root_config = wnode_misc.NodeConfig()
        txtp.begin(stinger.node, root_config, nname=stinger.ntrigger, ntid=stinger.ntrigger, ntidsub=stinger.ntid)

        #self._render_next(ntid, txtp)
        rnode = self._get_rnode(bnode)
        rnode._render_base(bnode, txtp)
        return

    #-------------------------------------

    def _get_rnode(self, bnode):
        if not bnode:
            return None

        # check is node already in cache
        #rnode = self._node_to_bnode.get(id(node))
        #if rnode:
        #    return rnode

        # rebuild node with a helper class and save to cache
        # (some banks get huge and call the same things again and again, it gets quite slow to parse every time)
        hircname = bnode.node.get_name()
        rclass = ru.get_renderer_hirc(hircname)

        rnode = rclass()
        rnode.init_renderer(self)

        #self._node_to_bnode[id(node)] = rnode
        return rnode

    #-------------------------------------

    # info when generating transitions
    def _register_transitions(self, txtp, ntransitions):
        for ntid in ntransitions:
            node = self._builder._get_transition_node(ntid)
            txtp.transitions.add(node)
        return
