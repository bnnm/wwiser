from ..registry import wparams


# Handles tree with multi gamesync (order of gamesyncs is branch order in tree)
#
# tree's args (gamesync key) are given in Arguments, and possible values in AkDecisionTree, that contains
# 'pNodes' with 'Node', that have keys (gamesync value) and children or audioNodeId:
#   Arguments
#       bgm
#           scene
#
#   AkDecisionTree
#       key=*
#           key=bgm001
#               key=scene001
#                   audioNodeId=123456789
#           key=*
#               key=*
#                   audioNodeId=234567890
#
# Thus: (-=*, bgm=bgm001, scene=scene001 > 123456789) or (-=*, bgm=*, scene=* > 234567890).
# Paths must be unique (can't point to different IDs).
#
# Wwise picks paths depending on mode:
# - "best match": (default) selects "paths with least amount of wildcards" (meaning favors matching values)
# - "weighted": random based on based on "weight" (0=never, 100=always)
# For example:
# (bgm=bgm001, scene=*, subscene=001) vs (bgm=*, scene=scene001, subscene=*) picks the later (less *)
#
# This behaves like "best match", but saves GS values as "*" (that shouldn't be possible)
#
# Trees always start with a implicit "*" key that matches anything, so it's possible
# to have trees with no arguments that point to an audioNodeId = non-switch tree


class AkDecisionTree(object):
    def __init__(self, node):
        self.init = False
        self.args = []
        self.paths = []
        self.tree = {}

        self._build(node)

    def _build(self, node):
        ntree = node.find(name='AkDecisionTree')
        if not ntree:
            return
        self.init = True

        # args has gamesync type+names, and tree "key" is value (where 0=any)
        depth = node.find1(name='uTreeDepth').value()
        nargs = node.finds(name='AkGameSync')
        if depth != len(nargs): #not possible?
            self._barf(text="tree depth and args don't match")

        self.args = []
        for narg in nargs:
            ngtype = narg.find(name='eGroupType')
            ngname = narg.find(name='ulGroup')
            if ngtype:
                gtype = ngtype.value()
            else: #DialogueEvent in older versions, assumed default
                gtype = wparams.TYPE_STATE
            self.args.append( (gtype, ngname) )

        # make a tree for access, plus a path list (similar to how the editor shows them) for GS combos
        # - [val1] = {
        #       [*] = { 12345 },
        #       [val2] = {
        #           [val3] = { ... }
        #       }
        #   }
        # - [(gtype1, ngname1, ngvalue1), (gtype2, ngname2, ngvalue2), ...] > ntid (xN)
        gamesyncs = [None] * len(nargs) #temp list

        nnodes = ntree.find1(name='pNodes') #always
        nnode = nnodes.find1(name='Node') #always
        npnodes = nnode.find1(name='pNodes') #may be empty
        if npnodes:
            self._build_tree_nodes(self.tree, 0, npnodes, gamesyncs)
        elif nnode:
            # In rare cases may only contain one node for key 0, no depth (NMH3). This can be added
            # as a "generic path" with no vars selected, meaning ignores vars and matches 1 object.
            self.ntid = nnode.find1(name='audioNodeId')


    def _build_tree_nodes(self, tree, depth, npnodes, gamesyncs):
        if depth >= len(self.args):
            self._barf(text="wrong depth") #shouldn't happen

        if not npnodes: #short branch?
            return
        nchildren = npnodes.get_children() #parser shouldn't make empty pnodes
        if not nchildren:
            return

        gtype, ngname = self.args[depth]

        for nnode in nchildren:
            ngvalue = nnode.find1(name='key')
            npnodes = nnode.find1(name='pNodes')
            gamesyncs[depth] = (gtype, ngname, ngvalue) #overwrite per node, will be copied

            key = ngvalue.value()

            if not npnodes: #depth + 1 == len(self.args): #not always correct
                ntid = nnode.find1(name='audioNodeId')
                tree[key] = (ngvalue, ntid, None)
                self._build_tree_leaf(ntid, ngvalue, gamesyncs)

            else:
                subtree = {}
                tree[key] = (ngvalue, None, subtree)
                self._build_tree_nodes(subtree, depth + 1, npnodes, gamesyncs)
        return

    def _build_tree_leaf(self, ntid, ngvalue, gamesyncs):
        # clone list of gamesyncs and final ntid (both lists as an optimization for huge trees)
        path = []
        for gamesync in gamesyncs:
            if gamesync is None: #smaller path, rare
                break
            gtype, ngname, ngvalue = gamesync
            path.append( (gtype, ngname.value(), ngvalue.value()) )
        self.paths.append( (path, ntid) )

        return

    def get_npath(self, params):
        # find gamesyncs matches in path

        # follow tree up to match, with implicit depth args
        npath = []
        curr_tree = self.tree
        for gtype, ngname in self.args:
            # current arg must be defined to some value
            gvalue = params.current(gtype, ngname.value())
            if gvalue is None: #not defined = can't match
                return None

            # value must exist in tree
            match = curr_tree.get(gvalue) # exact match (could match * too if gvalue is set to 0)
            if not match:
                match = curr_tree.get(0) # * match
            if not match:
                return None

            ngvalue, ntid, subtree = match
            npath.append( (gtype, ngname, ngvalue) )

            if not ntid:
                curr_tree = subtree # try next args = higher depth
            else:
                return (npath, ntid)

        return None
