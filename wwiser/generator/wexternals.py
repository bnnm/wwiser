import logging, os

# Reads a externals.txt list to get "externals", a type of .wem definition.
# Devs can manually set a "id <> filename" relation, and this simulates it.

class Externals(object):
    def __init__(self):
        self.active = False
        self._items = {}

    def get(self, item):
        return self._items.get(item)

    def load(self, banks):
        if not banks:
            return

        # take first bank as base folder (like .txtp), not sure if current (wwiser's) would be beter
        basepath = banks[0].get_root().get_path()
        in_name = os.path.join(basepath, 'externals.txt')
        if not os.path.exists(in_name):
            return

        logging.info("generator: found list of externals")

        with open(in_name, 'r') as in_file:
            current_tid = None
            current_list = None
            for line in in_file:
                line = line.strip()

                if not line or line.startswith('#'):
                    continue

                # new "cookie" ID
                if line.isnumeric():
                    current_tid = int(line)
                    if current_tid not in self._items:
                        self._items[current_tid] = []
                    current_list = self._items[current_tid]
                    continue

                # must have one
                if not current_tid:
                    logging.info("generator: WARNING, ignored externals (must start with an ID)")
                    return

                # add text under current ID
                current_list.append(line)

        self.active = bool(self._items)
