

# helper containing a single name

class NameRow(object):
    __slots__ = ['id', 'name', 'type', 'hashname', 'hashnames', 'guidname', 'guidnames', 'objpath', 'path', 'hashname_used', 'multiple_marked', 'source', 'extended', 'hashtypes']

    NAME_SOURCE_COMPANION = 0 #XML/TXT/H
    NAME_SOURCE_EXTRA = 1 #LST/DB

    def __init__(self, id, hashname=None):
        self.id = id

        self.hashname = hashname
        self.guidname = None
        self.hashnames = [] #for list generation (contains only extra names, main is in "hashname")
        self.guidnames = [] #possible but useful?
        self.path = None
        self.objpath = None
        self.hashname_used = False
        self.multiple_marked = False
        self.source = None
        self.extended = False
        self.hashtypes = None

    def _exists(self, name, list):
        if name.lower() in (listname.lower() for listname in list):
            return True
        return False

    def add_hashname(self, name, extended=False):
        if not name:
            return
        if not self.hashname: #base
            self.hashname = name
        else:
            if name.lower() == self.hashname.lower():
                return
            if name.lower() in (hashname.lower() for hashname in self.hashnames):
                return
            self.hashnames.append(name) #alts
        self.extended = extended

    def add_guidname(self, name):
        if not name:
            return
        if not self.guidname: #base
            self.guidname = name
        else:
            if name.lower() == self.guidname.lower():
                return
            if name.lower() in (guidname.lower() for guidname in self.guidnames):
                return
            self.guidnames.append(name) #alts

    def add_objpath(self, objpath):
        if not objpath:
            return
        self.objpath = objpath

    def add_path(self, path):
        if not path:
            return
        self.path = path
