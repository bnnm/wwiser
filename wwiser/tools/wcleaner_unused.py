import os, logging, re
from ..generator.render import bnode_source
import hashlib


# output folder is the same as original but using a extra mark
# /blah/blah > /blah/blah[unwanted]
# it's done that way since a subdir (/blah/blah/[unwanted]) would be re-included when loading *.bnk in subdirs
# in the rare case of moving in root, would probably throw an error (whatevs)
_OUTPUT_FOLDER_MARK = '[wwiser-unused]'
_OUTPUT_FOLDER_DUPE = '[wwiser-unused-dupes]'
_IS_TEST = False
_HASH_BUF_SIZE = 0x8000

_OBJECT_SOURCES = {
    'CAkSound': 'AkBankSourceData',
    'CAkMusicTrack': 'AkBankSourceData',
}

# moves .wem/bnk to extra folders
# - load referenced wem in all banks
# - load all existing .wem from root-path
# - move existing .wem that aren't referenced from (root)/(path) to (root-new)/(path)


class CleanerUnused(object):
    def __init__(self, locator, banks):
        self._locator = locator
        self._banks = banks
        self._nodes = []

        # shallow clone to remove from it 
        self._wems = self._locator.get_wems().copy()


        self._files_used = set()
        self._files_move = set()
        self._moved = 0
        self._errors = 0
        self._root_orig = None
        self._root_move = None
        self._root_dupe = None
        self._sizes_paths = {} #size > [path,...]
        self._hashes = {} #path > hash

    def process(self):
        self._prepare()
        logging.info("cleaner: moving unused files to %s", self._root_move)
        logging.info(" * make sure all banks are loaded to correctly classify unused")

        self._register_wems()
        if not self._nodes:
            logging.info("cleaner: no referenced wems found, can't detect unused")
            return

        self._parse_wems()
        if not self._wems.keys():
            logging.info("cleaner: no unused files to move")
            return

        # avoid odd cases of moving things outside root to root
        for file in self._files_move:
            if not file.startswith(self._root_orig):
                logging.info("cleaner: referenced files outside base folder, make sure base folder is loaded first")
                return


        self._move_files()

        logging.info("cleaner: moved %s files (%s errors)", self._moved, self._errors)
        if self._moved:
            logging.info(" * make sure files are really unused before removing them")

    def _prepare(self):
        root = self._locator.get_root_fullpath()
        self._root_move = root[0:-1] + _OUTPUT_FOLDER_MARK + '/'
        self._root_dupe = root[0:-1] + _OUTPUT_FOLDER_DUPE + '/'
        #root = os.path.abspath(root)
        self._root_orig = root


    def _register_wems(self):
        # similar to wgenerator._setup_nodes but since this cleaner is not commonly used...
        for bank in self._banks:
            root = bank.get_root()
            for nchunk in root.get_children():
                chunkname = nchunk.get_name()
                if chunkname == 'HircChunk':
                    items = bank.find(name='listLoadedItem')
                    if not items: # media-only banks don't have items
                        continue

                    for node in items.get_children():
                        self._add_node(node)

    def _add_node(self, node):
        hircname = node.get_name()
        node_name = _OBJECT_SOURCES.get(hircname)
        if node_name:
            nsources = node.finds(name=node_name)
            self._nodes.extend(nsources)

    def _parse_wems(self):
        for node in self._nodes:
            self._parse_wem(node)


    def _parse_wem(self, node):
        if not node:
            return

        source = bnode_source.AkBankSourceData(node, None)
        if not source or not source.tid: #?
            return
        #if source.tid in self._moved_sources:
        #    return
        if source.plugin_external or source.plugin_id: #not audio:
            return
        # media files for event-based audio are external
        #if source.internal:
        #    return

        # remove items, remaining keys will be considered unused
        items = self._wems.pop(source.tid, None)
        self._register_sizes(items)

    def _register_sizes(self, items):
        if not items:
            return
        root = self._root_orig

        for item in items:
            filepath = root + item[0] + item[1]
            try:
                file_size = os.path.getsize(filepath)
            except:
                logging.warn("cleaner: can't get filesize for %s", filepath)
                continue

            if file_size not in self._sizes_paths:
                self._sizes_paths[file_size] = []

            self._sizes_paths[file_size].append(filepath)

    def _move_files(self):
        for key in self._wems:
            items = self._wems[key]
            for items in items:
                file_part =  items[0] + items[1] #partial path without root
                self._move_file(file_part)


    def _move_file(self, file_part):
        root = self._root_orig
        outmove = self._root_move
        outdupe = self._root_dupe

        file = root + file_part
        if not os.path.isfile(file):
            logging.warn("cleaner: not found %s", file) #???
            print('ko', file)
            self._errors += 1
            return

        if self._is_file_dupe(file):
            outpath = outdupe
        else:
            outpath = outmove

        file_move = outpath + file[len(root) :]
        file_move = os.path.normpath(file_move)

        if _IS_TEST:
            print("move: ", file)
            print("      ", file_move)
            self._moved += 1
            return

        try:
            os.makedirs(os.path.dirname(file_move), exist_ok=True)
            os.rename(file, file_move)
            self._moved += 1
        except:
            self._errors += 1

    def _is_file_dupe(self, file):
        try:
            file_size = os.path.getsize(file)
        except:
            logging.warn("cleaner: can't get filesize for %s", file)


        items = self._sizes_paths.get(file_size)
        if not items:
            return False
        
        file_hash = self._get_hash(file)
        for item in items:
            if item not in self._hashes:
                item_hash = self._get_hash(item)
                if file_hash == item_hash:
                    logging.debug("cleaner: unused file %s is dupe of %s", file, item)
                    return True

        return False

    def _get_hash(self, file):
        if file in self._hashes:
            return self._hashes[file]

        md5 = hashlib.md5()
        with open(file, 'rb') as f:
            while True:
                data = f.read(_HASH_BUF_SIZE)
                if not data:
                    break
                md5.update(data)

        hash = md5.digest()
        self._hashes[file] = hash
        return hash
