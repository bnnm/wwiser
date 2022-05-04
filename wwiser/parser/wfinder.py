
# finds nodes in a node's tree based on config, external to simplify but could be optimized
# if added to model to avoid generating attrs dicts
class NodeFinder(object):
    def __init__(self, name=None, type=None, names=None, types=None, value=None, values=None, contains=None):
        if name:
            names = [name]
        if type:
            types = [type]
        if value is not None: #may be 0
            values = [value]
        if names is None:
            names = []
        if types is None:
            types = []
        if values is None:
            values = []
        self.names = names
        self.types = types
        self.values = values
        self.results = []
        self.first = False
        self.base = False
        self.contains = contains
        self.empty = not names and not types and not values and not contains


    def find1(self, node):
        return self.find(node, first=True)

    def find(self, node, first=False):
        if not node:
            return None
        self.first = first
        self.depth = 0

        # aim for outer nodes first as it's slightly faster in some cases
        #self._find_inner(node)
        self._find_outer([node])

        if self.results:
            if len(self.results) > 1:
                raise ValueError("more than 1 result found")
            return self.results[0]
        else:
            return None

    def finds(self, node):
        if not node:
            return []
        self.depth = 0

        # aim for outer nodes first as it's slightly faster in some cases
        #self._find_inner(node)
        self._find_outer([node])

        return self.results

    # find query in tree, going in depth first:
    # A > B > C
    #         > D
    #       > E
    #         > F
    #   > G
    # order: A B C D E F G (finds lower nodes faster)
    def _find_inner(self, node):
        if self.empty:
            return
        if self.first and self.results:
            return

        self._query(node)

        # target exists and only need one result: stop
        if self.first and self.results:
            return

        # keep finding results in children
        children = node.get_children()
        if not children:
            return
        for subnode in children:
            self.depth += 1
            self._find_inner(subnode)
            self.depth -= 1

    # find query in tree, going same-level first:
    # A > B > C
    #         > D
    #       > E
    #         > F
    #   > G
    # order: A B G C E D F (finds upper nodes faster)
    def _find_outer(self, nodes):
        if self.empty:
            return
        if self.first and self.results:
            return

        if not nodes:
            return

        # find query on this level
        for node in nodes:
            self._query(node)
            # target exists and only need one result: stop
            if self.first and self.results:
                return

        # find query on children level
        for node in nodes:
            self.depth += 1
            self._find_outer(node.get_children())
            self.depth -= 1
            # target exists and only need one result: stop
            if self.first and self.results:
                return


    def _query(self, node):
        #todo may simplify with a list of find key + value (like contains)
        # find target values in attrs
        #attrs = node.get_attrs()
        valid = self.depth > 0 or self.depth == 0 and self.base #first
        if not valid:
            return

        attr = node.get_attr('name')
        if attr:
            for target in self.names:
                if attr == target:
                    self.results.append(node)

        attr = node.get_attr('type')
        if attr:
            for target in self.types:
                if attr == target:
                    self.results.append(node)

        attr = node.get_attr('value')
        if attr is not None:
            for target in self.values:
                if attr == target:
                    self.results.append(node)

        if self.contains:
            key, val = self.contains
            attr = node.get_attr(key)
            if attr and val in attr:
                self.results.append(node)

        return


def node_find(node, name=None, type=None, names=None, types=None, value=None, values=None):
    finder = NodeFinder(name=name, type=type, names=names, types=types)
    return finder.find(node)

def node_finds(node, name=None, type=None, names=None, types=None, first=False, value=None, values=None):
    finder = NodeFinder(name=name, type=type, names=names, types=types, value=value, values=values)
    return finder.finds(node)
