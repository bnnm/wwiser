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

    # find gamesyncs matches in path, ex.
    # - defined:
    #    bgm=m01,bgm_vo=on  > 123
    #    bgm=m02,bgm_vo=on  > 345
    #    bgm=*  ,bgm_vo=off > 789
    # - paths
    #   - (bgm=m01,bgm_vo=on ): gets 123 (direct match)
    #   - (bgm=m01,bgm_vo=off): gets 789 (tries bgm=m01 but can't find bgm_vo=off, then tries bgm=* and matches bgm_vo=off)
    # Each part (bgm > bgm_vo) is defined in "args" at index N
    def get_npath(self, params):
        # Follow tree up to some match (recursive since it may need to re-try using other branches)
        # Result is [paths..] and should fill ntid, or set None

        self._leaf_ntid = None #meh
        npath = self._get_npath_sub(params, self.tree, 0)
        if not npath or not self._leaf_ntid:
            return None
        return (npath, self._leaf_ntid)

    # tree should be well formed and stop at some point when no match is found
    def _get_npath_sub(self, params, tree, args_index):
        if not tree: #args_index >= len(self.args):
            return None

        # current arg + params must be defined to some value
        gtype, ngname = self.args[args_index]

        gvalue = params.current(gtype, ngname.value())
        if gvalue is None: #not found in params = can't match
            return None

        npath = self._get_npath_submatch(params, tree, args_index, gvalue) # exact match
        if not npath:
            npath = self._get_npath_submatch(params, tree, args_index, 0)  # * match
        return npath

    def _get_npath_submatch(self, params, tree, args_index, gvalue):
        gtype, ngname = self.args[args_index]

        match = tree.get(gvalue)
        if not match:
            return None
        ngvalue, ntid, subtree = match

        npath = [(gtype, ngname, ngvalue)] #note paths are a list, combined on return
        if ntid: #leaf
            self._leaf_ntid = ntid
            return npath

        # next depth
        subnpath = self._get_npath_sub(params, subtree, args_index + 1)
        if subnpath:
            return npath + subnpath
        else:
            return None
