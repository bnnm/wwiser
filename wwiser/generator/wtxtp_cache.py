import logging, math, os
from . import wexternals, wstats
from .render import wmediaindex
from .txtp import wtxtp_renamer

DEFAULT_OUTDIR = 'txtp/'
DEFAULT_WEMDIR = 'wem/'
WINDOWS_INTERNAL_NAME = 'nt'

# config/cache/info for all txtp (updated during process)

class TxtpCache(object):
    def __init__(self):
        # process config
        self.outdir = DEFAULT_OUTDIR
        self.wemdir = DEFAULT_WEMDIR
        self.name_wems = False
        self.name_vars = False
        self.volume_master = None
        self.volume_master_auto = False
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
        self.wwnames = None
        self.statechunks_skip_default = False
        self.statechunks_skip_unreachables = False

        self.no_txtp = False
        self.x_noloops = False
        self.x_nameid = False
        self.x_silence_all = False
        self.x_include_fx = False

        # process helpers (passed around)
        self.tags = None
        self.mediaindex = wmediaindex.MediaIndex()
        self.externals = wexternals.Externals()
        self.renamer = wtxtp_renamer.TxtpRenamer()
        self.stats = wstats.Stats()

        # other helpers
        self.is_windows = os.name == WINDOWS_INTERNAL_NAME
        self.basedir = os.getcwd()

        self._common_base_path = None


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

    # when loading multiple bnk from different dirs we usually want all .txtp in the same base dir,
    # taken from the first .bnk
    def get_basepath(self, node):

        # allow separate dirs when using the lang flag? (harder to use)
        #if self.lang:
        #    return node.get_root().get_path()

        if self._common_base_path is None:
            self._common_base_path = node.get_root().get_path()
        return self._common_base_path
    
    def set_basepath(self, banks):
        if not banks:
            return
        node = banks[0]
        self._common_base_path = node.get_root().get_path()


    def set_master_volume(self, volume):
        if not volume:
            return

        # a few common cases to avoid a bunch of decimals
        VOLUME_PERCENT_TO_DB = {
            4.0: 12.0,
            2.0: 6.0,
            1.0: 0.0,
            0.5: -6.0,
            0.25: -12.0,
        }

        auto = False
        try:
            # use dB for easier mixing with Wwise's values
            if volume == '*':
                master_db = 0.0
                auto = True

            elif volume.lower().endswith('db'):
                master_db = float(volume[:-2])

            else:
                if volume.lower().endswith('%'):
                    master_db = float(volume[:-1]) / 100.0
                else:
                    master_db = float(volume)
                if master_db <= 0: #fails next formula, maybe should print something?
                    return
                master_db = VOLUME_PERCENT_TO_DB.get(master_db, math.log10(master_db) * 20.0)

            self.volume_master = master_db
            self.volume_master_auto = auto
        except ValueError: #not a float
            pass

        if volume and not self.volume_master and not auto:
            logging.info("parser: ignored incorrect master volume %s", volume)
