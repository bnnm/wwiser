import os

DEFAULT_OUTDIR = 'txtp/'
DEFAULT_WEMDIR = 'wem/'
WINDOWS_INTERNAL_NAME = 'nt'

# config/cache/info for all txtp (updated during process)

class TxtpCache(object):
    def __init__(self):
        # process config
        self.outdir = DEFAULT_OUTDIR
        self.wemdir = DEFAULT_WEMDIR
        self.wemnames = False
        self.volume_master = None
        self.volume_db = False
        self.volume_decrease = False
        self.lang = False
        self.bnkmark = False
        self.bnkskip = False
        self.alt_exts = False
        self.dupes = False
        self.dupes_exact = False
        self.random_all = False
        self.random_force = False
        self.tagsm3u = False
        self.silence = False

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

        # other helpers
        self.is_windows = os.name == WINDOWS_INTERNAL_NAME
        self.basedir = os.getcwd()

        self._txtp_hashes = {}
        self._name_hashes = {}
        self._banks = {}

        self._tag_names = {}

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

        if printer.has_internals():
            self.internals += 1
        if printer.has_streams():
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

    def get_tag_names(self):
        return self._tag_names

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

        percent = False
        if volume.lower().endswith('db'):
            volume = volume[:-2]
            self.volume_db = True
        elif volume.lower().endswith('%'):
            volume = volume[:-1]
            percent = True

        self.volume_master = float(volume)
        if percent:
            self.volume_master = self.volume_master / 100.0

        if self.volume_db:
            self.volume_decrease = (self.volume_master < 0)
        else:
            self.volume_decrease = (self.volume_master < 1.0)
