
class Stats(object):
    def __init__(self):
        # process info
        self.created = 0
        self.duplicates = 0
        self.unused = 0
        self.multitrack = 0
        self.trims = 0
        self.streams = 0
        self.internals = 0
        self.names = 0

        self._txtp_hashes = {} #hash
        self._namenode_hashes = {}
        self._name_hashes = {}
        self._banks = {}

        # process flag #TODO: improve
        self.unused_mark = False


    def register_txtp(self, texthash, printer):
        if texthash in self._txtp_hashes:
            self.duplicates += 1
            return False

        self._txtp_hashes[texthash] = True
        self.created += 1
        if self.unused_mark:
            self.unused += 1

        if printer.has_internals:
            self.internals += 1
        if printer.has_streams:
            self.streams += 1
        return True

    def unregister_dupe(self, texthash):
        if texthash in self._txtp_hashes:
            self.duplicates -= 1
        return

    def register_namenode(self, name, node):
        hashname = hash(name)
        hashnode = hash(node) #ok since different bank + cak object = different python hash
        key = (hashname, hashnode)

        self.names += 1
        if key in self._namenode_hashes:
            return False

        self._namenode_hashes[key] = True
        return True

    def register_namebase(self, name):
        # same as the above but without node/bank, to detect when it needs to rename
        hashname = hash(name)
        key = (hashname)

        if key in self._name_hashes:
            return False

        self._name_hashes[key] = True
        return True

    def current_name_count(self):
        return self.names

    def register_bank(self, bankname):
        self._banks[bankname] = True
        return

    def get_used_banks(self):
        return self._banks
