import os
from .. import wfnv

# Saves paths and returns appropriate values based on config.
# Example: loading from . (root)
#   ./music/BGM.bnk
#   ./music/123.wem
#   ./music/us/456.wem
# A .txtp in music/txtp/ may use ../BGM.bnk, ../123.wem, ../123/456.wem
# A .txtp in music/ may use BGM.bnk, etc
# A .txtp in ./ may use music/BGM.bnk, etc
#
# We need:
# - root-path: base from where bnk are loaded (may be a folder without banks that loads subfolders)
# - txtp-path: subdir from root-path where txtp are created
# - wem-path: subdir from txtp-path where wem are expected 
#   - can be autodetected to use paths where .wem exist in root-path relative to txtp-path

_CODEC_EXTENSION_NEW_VERSION = 62
_DEFAULT_ROOT_PATH = '.'
_DEFAULT_OUTDIR = 'txtp/'
_DEFAULT_WEMDIR = 'wem/'
_AUTO_PATH = '*'

class Locator(object):
    def __init__(self):
        self._version = None
        self._root_path = _DEFAULT_ROOT_PATH #may be full path
        self._txtp_path = _DEFAULT_OUTDIR
        self._wem_path = _DEFAULT_WEMDIR
        self._mod_path = ''

        self._fnv = wfnv.Fnv()

        self._auto_find = False
        self._init = False
        self._wems = {}
        self._bnks = {}
        self._externals = []

        self._auto_subdirs = False

        self._files = []
        #self._registered_bnk_paths = set()

    def set_root_path(self, path):
        if path is None:
            return
        self._root_path = self._normalize_path(path)

    def set_txtp_path(self, path):
        if path is None:
            return
        self._txtp_path = self._normalize_path(path)
        # extra: if path ends with '*', each txtp will be moved to a subdir
        # (note other features like the file cleaner don't properly work with this)
        if self._txtp_path and self._txtp_path.endswith('/*/'):
            self._txtp_path = self._txtp_path[0:-3]
            self._auto_subdirs = True

    def set_wem_path(self, path):
        if path is None:
            return

        if path == _AUTO_PATH:
            self._auto_find = True
        else:
            self._wem_path = self._normalize_path(path)

    def is_auto_find(self):
        return self._auto_find

    def register_banks(self, banks):
        if not banks:
            return
        # use first as base
        node = banks[0]
        self._version = node.get_root().get_version()

        #for bank in banks:
        #    path = node.get_root().get_path()
        #    self._registered_bnk_paths.add(path)

    # find wems from root-path and refer to them relative to txtp-path
    # (call after setting options to properly read paths)
    # TODO improve performance?
    def setup(self):
        if self._init:
            return
        self._init = True
        self._prepare_files()
        self._prepare_paths()

    #--------------------------------------------------------------------------

    def _prepare_paths(self):
        #if not self._auto_find: #useful?
        #    return

        # since wem-path is relative to txtp-path, detect how to move into root folder, ex:
        # (final path in .txtp would be mod-path + wem location, ex. '../' + 'sound/1.wem' in the first case)
        # - 'txtp/'         >  '../'
        # - 'out/txtp'      >  '../../'
        # - '.'             >  ''
        # - '../'           >  '(root)/'
        # - '../../'        >  '(preroot)/(root)/'
        # - '../txtp/'      >  '../(root)/'
        # - '../root/'      >  '.' #hard to detect

        self._mod_path = ''

        root_full = self._normalize_path(os.path.realpath(self._root_path))
        txtp_full = root_full + self._txtp_path
        rel_path = os.path.relpath(root_full, txtp_full)
        self._mod_path = self._normalize_path(rel_path)

    #--------------------------------------------------------------------------

    def _find_path(self, key, lang, items):
        # simple method: plain wem path (relative to txtp-path)
        if not self._auto_find or key is None:
            return self._wem_path

        # find wem path (from root folder) and include calc'd modifier (from txtp output folder)
        paths = items.get(key)
        if paths:
            path = self._mod_path + self._find_path_lang(paths, lang)
        else:
            path = self._wem_path #???

        if self._auto_subdirs:
            path = '../' + path
        return path

    # find most appropriate path given current wem/bnk's expected lang
    # lang is generally a normalized path (such as "SFX", "English(US)" but in rare cases could be hash.
    # Similarly paths may be names or hashes.
    def _find_path_lang(self, paths, lang):
        # TODO locator bug: if there are multiple bnks with the same name, sometimes internal wem is inside others
        # may need to register media wem <> bnk and use that ref
        # todo however if multiple .wem copies are found it should favor the shortest dir

        if not lang or len(paths) == 1: #or lang.lower() == 'sfx':
            return paths[0][0]

        # for rare cases with wems in multiple folders, last one is probably the best one (update?)
        if lang.lower() == 'sfx':
            return paths[-1][0]


        for path, _, dirlast, dirhash in paths:
            if lang.isdigit():
                if int(lang) == dirhash:
                    return path
            else:
                if lang == dirlast:
                    return path

        # shouldn't happen?
        return paths[0][0]

    def find_wem_path(self, sid, ext, lang):
        key = None
        if sid:
            key = int(sid)
        return self._find_path(key, lang, self._wems)

    def find_bnk_path(self, bnk, lang):
        key = None
        if bnk:
            key = bnk.lower()
        return self._find_path(key, lang, self._bnks)

    def find_externals(self):
        return self._externals

    def _prepare_files(self):

        if self._version < _CODEC_EXTENSION_NEW_VERSION:
            exts_wems = ['.ogg', '.logg', '.wav', '.lwav', 'xma']
        else:
            exts_wems = ['.wem']
        exts_bnks = ['.bnk']
        file_externals = ['externals.txt']

        # glob before certain version can't set root path nor check for multiple exts
        for root, _, files in os.walk(self._root_path):

            for file in files:
                if file.lower() in file_externals:
                    filepath = self._normalize_path(root) + file
                    self._externals.append(filepath)
                    # maybe should restrict only in bnk paths and root-path to avoid loading extra stuff, but externals aren't common
                    continue

                bn, ext = os.path.splitext(file)

                key = None
                if ext in exts_wems:
                    if not bn.isdigit(): #renamed wem?
                        continue
                    key = int(bn)
                    items = self._wems

                if ext in exts_bnks:
                    key = file.lower()
                    items = self._bnks

                if not key:
                    continue

                # save a list since may be multiple paths for the same wem/bnk, ex. localized audio or repeats for different updates
                if key not in items:
                    items[key] = []

                # prepare stuff for easier comparison
                path = self._normalize_path(root, cleanroot=True)
                dirs = path.split('/')
                if len(dirs) >= 2: #ends with '/'
                    dirlast = dirs[-2]
                else:
                    dirlast = ''
                if dirlast.isdigit(): #dir is already a hash
                    dirhash = int(dirlast)
                else:
                    dirhash = self._fnv.get_hash(dirlast)

                val = (path, file, dirlast, dirhash)
                items[key].append(val)

                self._files.append(path + file)

    # base path where txtp are generated
    def get_txtp_rootpath(self):
        outdir = self._root_path #important in GUI since work dir may be different
        txtp_path = self._txtp_path
        if txtp_path:
            outdir = os.path.join(outdir, txtp_path)
        return outdir

    # final txtp path
    def get_txtp_fullpath(self, node):
        outdir = self.get_txtp_rootpath()
        if self._auto_subdirs and node:
            bank = node.get_root().get_filename()
            lang = node.get_root().get_lang()

            bank = os.path.splitext(bank)[0]
            localized = lang != 0 and lang != 393239870 #early or regular SFX
            if localized:
                bank = '%s[%s]' % (bank, 'localized')

            outdir = os.path.join(outdir, bank)
        return outdir

    def get_root_fullpath(self):
        return self._root_path #important in GUI since work dir may be different

    def get_wem_fullpath(self):
        if self._auto_find:
            return ''
        outdir = self.get_txtp_rootpath()
        if self._wem_path:
            outdir = os.path.join(outdir, self._wem_path)

        return outdir

    # paths for txtp
    def _normalize_path(self, path, cleanroot=False):
        #path = path or '' #better?
        if path is None:
            path = ''
        path = path.strip()
        path = path.replace('\\', '/')
        if path and not path.endswith('/'):
            path += '/'
        if path.startswith('./'):
            path = path[2:]

        if cleanroot and path.startswith(self._root_path):
            path = path[len(self._root_path):]

        return path

    def clean_path(self, path):
        return self._normalize_path(path, cleanroot=True)

    def get_files(self):
        return self._files

    def get_wems(self):
        return self._wems
