
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

        self._txtp_hashes = {}
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

    def register_name(self, name):
        hashname = hash(name)

        self.names += 1
        if hashname in self._name_hashes:
            return False

        self._name_hashes[hashname] = True
        return True

    def current_name_count(self):
        return self.names

    def register_bank(self, bankname):
        self._banks[bankname] = True
        return

    def get_used_banks(self):
        return self._banks
