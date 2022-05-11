from . import wnode_misc
from . import wrenderer_util as ru
from . import wrenderer_nodes as rn


TEST_NEW = False

class Renderer(object):
    def __init__(self, builder):
        self._builder = builder

    def get_generated_hircs(self):
        return ru.GENERATED_BASE_HIRCS


    def begin_txtp(self, txtp, node):
        bnode = self._builder._get_bnode(node)
        if not bnode:
            return

        self._root_node = node #info for transitions

        root_config = wnode_misc.NodeConfig()
        txtp.begin(node, root_config)

        if TEST_NEW:
            rnode = self._get_rnode(bnode)
            rnode._make_txtp(bnode, txtp)
        else:
            bnode._make_txtp(txtp)

        self._root_node = None #info for transitions
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

        #self._process_next(ntid, txtp)
        root_config = wnode_misc.NodeConfig()
        txtp.begin(stinger.node, root_config, nname=stinger.ntrigger, ntid=stinger.ntrigger, ntidsub=stinger.ntid)
        
        if TEST_NEW:
            rnode = self._get_rnode(bnode)
            rnode._make_txtp(bnode, txtp)
        else:
            bnode._make_txtp(txtp)
        return

    #-------------------------------------

    # info when generating transitions
    def _register_transitions(self, txtp, ntransitions):
        for ntid in ntransitions:
            node = self.builder._get_transition_node(ntid)
            txtp.transitions.add(node)
        return


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
        rnode.init_builder(self._builder)
        rnode.init_renderer(self)

        #self._node_to_bnode[id(node)] = rnode
        return rnode
