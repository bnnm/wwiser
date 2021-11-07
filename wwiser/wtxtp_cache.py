import math, os
from . import wtxtp_namer

DEFAULT_OUTDIR = 'txtp/'
DEFAULT_WEMDIR = 'wem/'
WINDOWS_INTERNAL_NAME = 'nt'

# a few common cases to avoid a bunch of decimals
VOLUME_PERCENT_TO_DB = {
    4.0: 12.0,
    2.0: 6.0,
    1.0: 0.0,
    0.5: -6.0,
    0.25: -12.0,
}
# config/cache/info for all txtp (updated during process)

class TxtpCache(object):
    def __init__(self):
        # process config
        self.outdir = DEFAULT_OUTDIR
        self.wemdir = DEFAULT_WEMDIR
        self.name_wems = False
        self.name_vars = False
        self.volume_master = None
        self.lang = False
        self.bnkmark = False
        self.bnkskip = False
        self.alt_exts = False
        self.dupes = False
        self.dupes_exact = False
        self.random_all = False
        self.random_multi = False
        self.random_force = False
        self.write_delays = False
        self.silence = False

        # helpers
        self.tags = None
        self.renamer = wtxtp_namer.TxtpRenamer()

        self.x_noloops = False
        self.x_notxtp = False
        self.x_nameid = False

        # process info
        self.created = 0
        self.duplicates = 0
        self.unused = 0
        self.multitrack = 0
        self.trims = 0
        self.streams = 0
        self.internals = 0
        self.names = 0

        # externals
        self.externals = None

        # other helpers
        self.is_windows = os.name == WINDOWS_INTERNAL_NAME
        self.basedir = os.getcwd()

        self._txtp_hashes = {}
        self._name_hashes = {}
        self._banks = {}

        self.transition_mark = False
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


    def register_bank(self, bankname):
        self._banks[bankname] = True
        return

    def get_banks(self):
        return self._banks


    # paths for txtp
    def normalize_path(self, path):
        #path = path or '' #better?
        if path is None:
            path = ''
        path = path.strip()
        path = path.replace('\\', '/')
        if path and not path.endswith('/'):
            path += '/'
        return path

    def get_txtp_dir(self):
        dir = ''
        if self.outdir:
            dir += self.outdir
        if self.wemdir:
            dir += self.wemdir
        return dir

    def set_volume(self, volume):
        if not volume:
            return

        try:
            # use dB for easier mixing with Wwise's values
            if volume.lower().endswith('db'):
                master_db = float(volume[:-2])
            else:
                if volume.lower().endswith('%'):
                    master_db = float(volume[:-1]) / 100.0
                else:
                    master_db = float(volume)
                if master_db < 0:
                    return
                master_db = VOLUME_PERCENT_TO_DB.get(master_db, math.log10(master_db) * 20.0)

            self.volume_master = master_db
        except ValueError: #not a float
            return
