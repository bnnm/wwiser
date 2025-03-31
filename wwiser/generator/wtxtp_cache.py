import logging, math, os
from . import wexternals, wstats
from .render import wmediaindex
from .txtp import wtxtp_renamer

WINDOWS_INTERNAL_NAME = 'nt'

# config/cache/info for all txtp (updated during process)

class TxtpCache(object):
    def __init__(self):
        # process config
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
        self.x_prefilter_paths = False

        # process helpers (passed around)
        self.locator = None
        self.tags = None
        self.mediaindex = wmediaindex.MediaIndex()
        self.externals = wexternals.Externals()
        self.renamer = wtxtp_renamer.TxtpRenamer()
        self.stats = wstats.Stats()

        # other helpers
        self.is_windows = os.name == WINDOWS_INTERNAL_NAME
        self.basedir = os.getcwd()

        self._common_base_path = None


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
        volume = volume.replace(" ", "") # "* + 3.0 db" > "*+3.0db"
        try:
            # use dB for easier mixing with Wwise's values
            for text in ['*','auto']:
                if volume.startswith(text):
                    master_db = 0.0
                    auto = True
                    # allow *+3.0db = auto volume then adds 3.0db
                    volume = volume[len(text):]
                    break

            if not volume: #in case of auto volume
                pass

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
