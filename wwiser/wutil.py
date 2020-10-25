import os, logging, pkgutil


def setup_clean_logging():
    # removes old handlers in case we call one setup after other setups
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

#to-do: handlers is python3.3+?
def setup_cli_logging():
    setup_clean_logging()
    #handlers = [logging.StreamHandler(sys.stdout)]
    logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            #format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
            #handlers=handlers
    )

def setup_gui_logging(txt):
    setup_clean_logging()
    handlers = [_GuiLogHandler(txt)]
    logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            #format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
            handlers=handlers
    )

def setup_file_logging():
    setup_clean_logging()
    #handlers = [logging.FileHandler('wwiser.log')]
    logging.basicConfig(
            #allow DEBUG for extra info
            level=logging.DEBUG,
            format='%(message)s',
            #format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
            filename='wwiser.log'
    )

class _GuiLogHandler(logging.Handler):
    def __init__(self, txt):
        logging.Handler.__init__(self)
        self._txt = txt

    def emit(self, message):
        msg = self.format(message)
        self._txt.config(state='normal')
        self._txt.insert('end', msg + '\n')
        self._txt.config(state='disabled')

# *****************************

class _Loader(object):
    def __init__(self):
        pass

    def get_resource_text(self, path):
        try:
            return pkgutil.get_data(__name__, path).decode()
        except (FileNotFoundError, OSError): # as e
            return None

    def get_resource(self, path):
        try:
            return pkgutil.get_data(__name__, path)
        except (FileNotFoundError, OSError): # as e
            return None

Loader = _Loader()

#******************************************************************************

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
        self._find(node)
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
        self._find(node)
        return self.results

    def _find(self, node):
        if self.empty:
            return
        if self.first and self.results:
            return

        #attrs = node.get_attrs()
        children = node.get_children()

        #todo may simplify with a list of find key + value (like contains)
        # find target values in attrs
        ignore = self.depth > 0 or self.depth == 0 and self.base #first
        if ignore:
            attr = node.get_attr('name')
            #if 'name' in attrs:
            if attr:
                for target in self.names:
                    if attr == target:
                    #if attrs['name'] == target:
                        self.results.append(node)

            attr = node.get_attr('type')
            if attr:
            #if 'type' in attrs:
                for target in self.types:
                    #if attrs['type'] == target:
                    if attr == target:
                        self.results.append(node)

            attr = node.get_attr('value')
            if attr is not None:
            #if 'value' in attrs:
                for target in self.values:
                    if attr == target:
                    #if attrs['value'] == target:
                        self.results.append(node)
            if self.contains:
                key, val = self.contains
                attr = node.get_attr(key)
                if attr and val in attr:
                #if key in attrs and val in attrs[key]:
                    self.results.append(node)


        # target exists and only need one result: stop
        if self.first and self.results:
            return

        # keep finding results in children
        if children:
            for subnode in children:
                self.depth += 1
                self._find(subnode)
                self.depth -= 1

def node_find(node, name=None, type=None, names=None, types=None, value=None, values=None):
    finder = NodeFinder(name=name, type=type, names=names, types=types)
    return finder.find(node)

def node_finds(node, name=None, type=None, names=None, types=None, first=False, value=None, values=None):
    finder = NodeFinder(name=name, type=type, names=names, types=types, value=value, values=values)
    return finder.finds(node)
