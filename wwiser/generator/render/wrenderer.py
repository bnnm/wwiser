from . import wnode_misc
from . import wrebuilder_util as ru



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
        bnode._make_txtp(txtp)
        return
