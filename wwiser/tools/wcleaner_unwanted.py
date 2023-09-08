import os, logging, re


# output folder is the same as original but using a extra mark
# /blah/blah > /blah/blah[unwanted]
# it's done that way since a subdir (/blah/blah/[unwanted]) would be re-included when loading *.bnk in subdirs
# in the rare case of moving in root, would probably throw an error (whatevs)
_OUTPUT_FOLDER_MARK = '[wwiser-unwanted]'
_IS_TEST = False
_IS_TEST_DIR = False

# moves .wem/bnk to extra folders
# - load all existing .wem/bnk from root-path
# - load .txtp in txtp-path
# - remove used files from existing
# - move remaining files from (root)/(path) to (root-new)/(path)
#
# (maybe should have a .zip option but that doesn't let you check bgm files not in txtp)

# catch folder-like parts followed by name + extension
_FILE_PATTERN = re.compile(r"^[ ]*[?]*[ ]*([0-9a-zA-Z_\- \\/\.]*[0-9a-zA-Z_]+\.[0-9a-zA-Z_]+).*$")
# catch comment with .bnk used to generate current .txtp
_BANK_PATTERN = re.compile(r"^#[ ]*-[ ]*([0-9a-zA-Z_\- \\/\.]*[0-9a-zA-Z_]+\.bnk).*$")

class CleanerUnwanted(object):
    def __init__(self, locator):
        self._locator = locator
        self._files_used = set()
        self._files_move = set()
        self._moved = 0
        self._errors = 0
        self._root_orig = None
        self._root_move = None
        self._dirs_moved = set()

    def process(self):
        self._prepare()
        logging.info("cleaner: moving unwanted files to %s", self._root_move)

        self._parse_txtps()
        if not self._files_used:
            logging.info("cleaner: no txtp or referenced files found")
            return

        self._parse_files()
        if not self._files_move:
            logging.info("cleaner: no unwanted files to move")
            return

        # avoid odd cases of moving things outside root to root
        for file in self._files_move:
            if not file.startswith(self._root_orig):
                logging.info("cleaner: referenced files outside base folder, make sure base folder is loaded first")
                return


        self._move_files()
        self._clean_dirs()

        logging.info("cleaner: moved %s files (%s errors)", self._moved, self._errors)
        if self._moved:
            logging.info(" * make sure files are really unwanted before removing them")

    def _prepare(self):
        root = self._locator.get_root_fullpath()
        outpath = root[0:-1] + _OUTPUT_FOLDER_MARK + '/'
        root = os.path.abspath(root)
        self._root_orig = root
        self._root_move = outpath
        

    def _parse_txtps(self):
        base_root = self._locator.get_root_fullpath()
        txtp_root = self._locator.get_txtp_fullpath()
        try:
            filenames = os.listdir(txtp_root)
        except:
            return

        for filename in filenames:
            if not filename.endswith('.txtp'):
                continue
            txtp = os.path.join(txtp_root, filename)
            with open(txtp, 'r', encoding='utf-8-sig') as infile:
                for line in infile:
                    if line.startswith('#'):
                        match = _BANK_PATTERN.match(line)
                        extra_bank = True
                    else:
                        match = _FILE_PATTERN.match(line)
                        extra_bank = False

                    if not match:
                        continue
                    name, = match.groups()
                    file = name.replace('\\', '/')

                    #file = os.path.normpath(name)
                    #file = os.path.normcase(file)
                    #path = os.path.dirname(file)
                    if extra_bank:
                        filepath = os.path.join(base_root, file) #relative to root dir
                    else:
                        filepath = os.path.join(txtp_root, file) #relative to txtp dir
                    filepath = os.path.abspath(filepath)
                    self._files_used.add(filepath)
                    #self._folders_used.add(path)

                    #if extra_bank:
                    #    print(filepath)

    def _parse_files(self):
        root = self._locator.get_root_fullpath()
        files = self._locator.get_files() #.wem and .bnk only
        for file in files:
            filepath = file

            if not file.startswith(root): #for GUI
                filepath = os.path.join(root, filepath)
                filepath = os.path.abspath(filepath)
            
            if filepath in self._files_used:
                continue

            self._files_move.add(filepath)

    def _move_files(self):
        for file in self._files_move:
            bn = os.path.basename(file)
            _, ext = os.path.splitext(bn)

            ignore = False
            for bnk in ['init.bnk', '1355168291.bnk']:
                if bnk in bn.lower():
                    ignore = True
                    break
            if ignore:
                continue

            if ext == '.bnk' or ext == '.BNK':
                move_exts = ['.bnk', '.txt', '.xml','.json']
                if ext == '.BNK': #probably unneeded but...
                    move_exts = [ item.upper() for item in move_exts]

                # move .bnk + companion files if any
                for move_ext in move_exts:
                    file_tmp = file.replace(ext, move_ext)
                    self._move_file(file_tmp)
            else:
                self._move_file(file)


    def _move_file(self, file):
        if not os.path.isfile(file):
            return

        #file = os.path.normpath(name)

        root = self._root_orig
        outpath = self._root_move
        if not file.startswith(root):
            raise ValueError("unexpected path", file)

        file_move = outpath + file[len(root) :]
        file_move = os.path.normpath(file_move)

        dir_move = os.path.dirname(file)
        self._dirs_moved.add(dir_move)

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

    def _clean_dirs(self):
        
        dirs = list(self._dirs_moved)
        dirs.reverse() #in case of subdirs this (probably) should remove them correctly

        for dir in dirs:
            if not os.path.isdir(dir):
                logging.warning("cleaner: not a dir? %s", dir)
                continue
            items = os.listdir(dir)
            if items:
                continue

            if _IS_TEST_DIR:
                print("remove dir:", dir)
                continue

            try:
                os.rmdir(dir)
            except:
                logging.warning("cleaner: dir error? %s", dir)
