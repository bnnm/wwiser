import logging, re, os, os.path, sys, sqlite3
from datetime import datetime


# Parses various companion files with names and saves results, later used to assign names to bank's
# ShortIDs. Resulting name list may be either ID=HASHNAME, where ID is a hash of HASHNAME (events,
# game syncs, soundsbanks, possibly others), or ID=GUIDNAME where it'a hash of the GUID (other objects).
# No need to know intended target (event vs wem) since names can be tested to be hashname or not.
#
# For hashnames, Wwise enforces that names must be unique in the same proyect, but the hashing
# algorithm is simple and prone to collisions. When parsing companion files, game's files should
# be loaded before generic (wwnames.db3) name lists, to minimize the chance to load wrong names.
# Hashnames are case insensitive, but SoundbanksInfo.xml may have Play_Thing while Wwise_IDs.h
# hash PLAY_THING. This code doesn't normalize names so priority is given to the former.
# GUIDNAMEs may be given multiple variations in different files too.
#
# IDs may also have an "object path" (logical) or "path" (physical), that are never a HASHNAMEs,
# but give extra hints.
#******************************************************************************

class Names(object):
    ONREPEAT_INCLUDE = 1
    ONREPEAT_IGNORE = 2
    ONREPEAT_BEST = 3


    def __init__(self):
        #self._gamename = None #info txt
        self._bankname = None
        self._names = {}
        self._names_fuzzy = {}
        self._db = None
        self._loaded_banknames = {}
        self._missing = {}
        self._fnv = Fnv()

    def set_gamename(self, gamename):
        self._gamename = gamename #path

    def get_namerow(self, id, hashtype=None):
        if not id or id == -1: #including id=0, that is used as "none"
            return None
        id = int(id)
        no_hash = hashtype == 'none'

        # on list
        row = self._names.get(id)
        if row:
            # in case of guidnames don't mark but allow row
            if not (row.hashname and no_hash):
                row.hashname_used = True
            return row

        # hashnames not allowed
        if no_hash:
            # next tests only find ids with hashnames
            return None

        # on list with a close ID
        id_fz = id & 0xFFFFFF00
        row_fz = self._names_fuzzy.get(id_fz)
        if row_fz and row_fz.hashname:
            hashname_uf = self._fnv.unfuzzy_hashname(id, row_fz.hashname)
            row = self._add_name(id, hashname_uf, source=NameRow.NAME_SOURCE_EXTRA)
            if row:
                row.hashname_used = True
                return row

        if not self._db:
            return None

        # on db (add to names for easier access and saving list of wwnames)
        row_db = self._db.select_by_id(id)
        if row_db:
            row = self._add_name(id, row_db.hashname, source=NameRow.NAME_SOURCE_EXTRA)
            if row:
                row.hashname_used = True
                return row

        # on db with a close ID
        row_df = self._db.select_by_id_fuzzy(id)
        if row_df and row_df.hashname:
            hashname_uf = self._fnv.unfuzzy_hashname(id, row_df.hashname)
            row = self._add_name(id, hashname_uf, source=NameRow.NAME_SOURCE_EXTRA)
            if row:
                row.hashname_used = True
                return row

        # groups missing ids by types (uninteresting ids like AkSound don't pass type)
        if hashtype:
            if hashtype not in self._missing:
                self._missing[hashtype] = {}
            self._missing[hashtype][id] = True

        return None

    # IDs come from hashed NAME (32b, where name follows rules) or hashed GUIDs (30b, where NAME is arbitrary),
    # so first we check the type. Sometimes IDs that should come from GUID (like BUS names, according to
    # AK's docs) are actually from NAMEs, so it's worth manually testing rather than trusting the caller.
    # Multiple GUIDNAMEs for an ID are possible, so we can update the results, and we can also add Wwise's
    # "Path/ObjectPath" for extra info (never hashnames, considered separate).
    def _add_name(self, id, name, objpath=None, path=None, onrepeat=ONREPEAT_INCLUDE, forcehash=False, source=None):
        if name:
            name = name.strip()
        if not name: #after strip
            return None

        lowname = name.lower()
        hashable = self._fnv.is_hashable(lowname)
        if not id and not forcehash and not hashable:
            return None
        id_hash = self._fnv.get_hash(lowname)

        if not id:
            id = id_hash
        else:
            id = int(id)
        is_hashname = id == id_hash

        row = self._names.get(id)
        if row:
            #ignore even if guidname
            if onrepeat == self.ONREPEAT_IGNORE:
                return row

            if is_hashname and row.hashname:
                if row.hashname.lower() != name.lower():
                    logging.info("names: alt hashname (using old), old=%s vs new=%s" % (row.hashname, name))
                    #return None #allow to add as alt
                    pass
                # ignore new name if all uppercase (favors lowercase names)
                if onrepeat == self.ONREPEAT_BEST and name.isupper():
                    #logging.info("names: ignoring new uppercase name, new=%s vs old=%s" % (name, row.hashname))
                    return None
                #logging.info("names: updating row, new=%s vs old=%s" % (name, row.hashname))
        else:
            row = NameRow(id)
            row.source = source
            self._names[id] = row

        if is_hashname:
            row.add_hashname(name)
            #logging.info("names: added id=%i, hashname=%s" % (id, name))
        else:
            row.add_guidname(name)
            #logging.info("names: added id=%i, guidname=%s" % (id, name))

        if objpath:
            row.add_objpath(objpath)
            #logging.info("names: added id=%i, objpath=%s" % (id, objpath))

        if path:
            row.add_path(path)
            #logging.info("names: added id=%i, path=%s" % (id, path))

        # reference to get close names
        if row.hashname:
            id_fuzzy = id & 0xFFFFFF00
            self._names_fuzzy[id_fuzzy] = row #latest row is ok

        # in case it was registered
        if is_hashname:
            for hashtype in self._missing:
                if id in self._missing[hashtype]:
                    del self._missing[hashtype][id]

        return row

    # *************************************

    def parse_files(self, filenames, xml=None, txt=None, h=None, lst=None, db=None):
        if not filenames:
            return

        # parse files for a single bank
        for filename in filenames:
            # update current bank name (in case of mixed bank dirs; repeats aren't parsed again)
            self.set_bankname(filename)

            # from more to less common/useful
            self.parse_xml(xml)
            self.parse_txt(txt)
            self.parse_h(h)

            # bank is usually hashed and used as bank's sid (add after actual files)
            base_bankname = os.path.basename(self._bankname) #[:-4] #
            base_bankname = os.path.splitext(base_bankname)[0]
            self._add_name(None, base_bankname, source=NameRow.NAME_SOURCE_EXTRA)

        # extra files, after other banks or priority when generating some missing lists and stuff is off
        pathfiles = [filenames[0]] #todo fix for multiple paths in filenames, for now assumes one
        for pathfile in pathfiles:
            self.set_bankname(pathfile)

            # from more to less common/useful
            self.parse_lst(lst)
            self.parse_db(db)


    def _parse_base(self, filename, callback, reverse_encoding=False):
        encodings = ['utf-8', 'iso-8859-1']
        if reverse_encoding:
            encodings.reverse()
        try:
            if not os.path.isfile(filename):
                return

            if filename in self._loaded_banknames:
                #logging.info("names: ignoring already loaded file " + filename)
                return

            #try encodings until one works
            done = False
            for encoding in encodings:
                try:
                    with open(filename, 'r', encoding=encoding) as infile:
                        callback(infile)
                        done = True
                    break
                except UnicodeDecodeError:
                    #logging.info("names: file %s failed with encoding %s, trying others", filename, encoding)
                    continue

            if not done:
                logging.info("names: error reading file %s (change encoding?)", filename)

        except Exception as e:
            logging.error("names: error reading name file " + filename, e)
        # save even on error to avoid re-reading the same wrong file
        self._loaded_banknames[filename] = True


    #Wwise_IDs.h
    # C++ namespaces with callable constants, as "NAME = ID". Possible namespaces (all inside from "AK"):
    # - EVENTS > (NAME) = (id)
    # - DIALOGUE_EVENTS > (NAME) = (names)
    # - STATES > (STATE GROUP NAMES) > GROUP = (group name) > STATE > (NAME) = (name)
    # - SWITCHES > (SWITCH GROUP NAMES) > GROUP = (name) > SWITCH > (NAME) = (name)
    # - ARGUMENTS > (ARGUMENT GROUP NAMES) > ARGUMENT = (name) > ARGUMENT_VALUE > (NAME) = (name) #older
    # - GAME_PARAMETERS > (NAME) = (name)
    # - TRIGGERS > (NAME) = (name)
    # - BANKS > (NAME) = (name)
    # - BUSSES > (NAME) = (name)
    # - AUX_BUSSES > (NAME) = (name)
    # - AUDIO_DEVICES > (NAME) = (name)
    # - EXTERNAL_SOURCES : (name)
    # - ENVIRONMENTALS > (ENV NAME) > PROPERTY_SET > (NAME) = (hashname)
    # We can just get (NAME) = (ID) and ignore namespaces, except for GROUP/ARGUMENT/etc "pseudo-namespaces"
    # whose ID actually corresponds to the parent namespace name. Since having to know every "pseudo-namespace"
    # isn't very operative just hash the namespace, and if we find a GROUP = id where the ID already
    # exists (the hashed namespace right before) ignore that id+name.
    def parse_h(self, filename=None):
        if not filename:
            filename = self._make_filepath('Wwise_IDs.h') #maybe should try in ../ too?
        self._parse_base(filename, self._parse_h)

    def _parse_h(self, infile):
        #catch ".. static const AkUniqueID THING = 12345U;" lines
        pattern_ct = re.compile(r"^.+ AkUniqueID ([a-zA-Z_][a-zA-Z0-9_]*) = ([0-9]+).*")
        #catch ".. namespace THING", while ignoring ".. // namespace THING" lines
        pattern_ns = re.compile(r"^.+[^/].+ namespace ([a-zA-Z_][a-zA-Z0-9_]*).*")

        for line in infile:
            match = pattern_ct.match(line)
            if match:
                name, id = match.groups()
                self._add_name(id, name, onrepeat=Names.ONREPEAT_IGNORE)
                continue

            match = pattern_ns.match(line)
            if match:
                id = None
                name, = match.groups()
                self._add_name(id, name)


    #(bankname).txt
    # CSV-like format, with section headers and section data (without spaces)
    # (Section name)\t  ID\t    Name\t  (extra fields and \t depending on section)
    # \t  (id)\t    (name)\t    (...)
    # (xN)
    # (empty line, then next section)
    #
    # Sections may be "Event", "Bus", "In Memory" (wem), "Streamed Audio" (wem), and so on.
    # Ultimately we only need \t(id)\t(name). Extra fields usually include the editor's
    # object path (like "\Events\Default Work Unit\Pause_All" for event "Pause_All", or
    # full giant .wem path like D:\Jenkins\ws\wwise_v2019.2\.....\Bass160 Fight3_2D88AD03.wem)
    # Consistently Paths go after 3 tabs (except for wem paths), while other sections use 1 tab.
    # "State" (not "State Groups")'s path is actually the state group (could be separated)
    # Wem names can be anything, so we want to capture any text
    #
    # Encoding on Windows is cp-1252 (has 0xA9=copyright), maybe Linux/Mac would use
    # UTF-8, but those symbols seem only used in comments so shouldn't matter too much
    # (other than Python throwing exceptions on unknown chars).
    #
    def parse_txt(self, filename=None):
        if not filename:
            filename = os.path.splitext(self._bankname)[0] + '.txt'
        self._parse_base(filename, self._parse_txt, reverse_encoding=True)

    def _parse_txt(self, infile):
        #catch: "	1234155799	Play_Thing			\Default Work Unit\Play_Thing	" (with path being optional)
        #pattern_ph = re.compile("^\t([0-9]+)\t([a-zA-Z_][a-zA-Z0-9_ ]*)(\t\t\t([^\t]+))?.*")
        pattern_ph = re.compile(r"^\t([0-9]+)\t([^\t]+)(\t\t*?\t*?([^\t]+))?.*")

        for line in infile:
            match = pattern_ph.match(line)
            if match:
                id, name, dummy, objpath = match.groups()
                self._add_name(id, name, objpath=objpath)


    #SoundbanksInfo.xml
    # An XML with info about bank objects. Main targets are:
    # - <(object) Id="(id)" Name="(name)" ...
    # - <(object) Id="(id)" ...>\n ...  <ShortName>(name)</ShortName> <Path>(path)</Path>...
    # Names are hashnames, while ShortNames/Paths may be anything (including UTF-8), usually
    # Paths is the real file ("sfx/file.wav"), while ShortName is may be shared (like multi-lang
    # .wem with same ShortName but different Paths) and can be a hashname. Other attrs include
    # ObjectPath (not too useful, see .txt info). Some tags are just IDs
    # links without name though.
    # The XML can be big (+20MB) and since we don't need all details and just id/names it can be
    # parsed as simple text to increase performance.
    def parse_xml(self, filename=None):
        if not filename:
            filename = self._make_filepath('SoundbanksInfo.xml')
        self._parse_base(filename, self._parse_xml)

    def _parse_xml(self, infile):
        #catch: "	<Thing Id="12345" Name="Play_Thing" ObjectPath="\Default Work Unit\Play_Thing">"
        pattern_in = re.compile(r"^.*<.+ Id=[\"]([0-9]+)[\"] .*Name=[\"]([a-zA-Z0-9_]+)[\"](.* ObjectPath=[\"](.+)[\"])?.+")
        #catch: "	<Thing Id="12345" Language="SFX">"
        #       "		<ShortName>Thing-Stuff.wem</ShortName>"
        pattern_id = re.compile(r"^.*<.+ Id=[\"]([0-9]+)[\"] .+")
        pattern_sn = re.compile(r"^.*<ShortName.*>(.+?)</ShortName.*>")
        pattern_pa = re.compile(r"^.*<Path.*>(.+?)</Path.*>")
        pattern_ob = re.compile(r"^.*<ObjectPath.*>(.+?)</ObjectPath.*>")

        id = name = objpath = path = None
        for line in infile:
            # accept id + name (+ objpath)
            match = pattern_in.match(line)
            if match:
                # prev id + shortname still hanging around
                if id and name:
                    self._add_name(id, name, objpath=objpath, path=path)

                id, name, dummy, objpath = match.groups()
                self._add_name(id, name, objpath=objpath)
                id = name = objpath = path = None
                continue


            # try id (may change multiple times)
            match = pattern_id.match(line)
            if match:
                # prev id + shortname still hanging around
                if id and name:
                    self._add_name(id, name, objpath=objpath, path=path)

                id = name = objpath = path = None
                id, = match.groups()
                continue

            # If id was found (in the above match or a previous one) try parts, id + shortname
            # must exists and the others are optional (possible to get all).
            # This assumes an id is followed by names, could get fooled in some cases.
            if id:
                match = pattern_sn.match(line)
                if match:
                    name, = match.groups()
                    continue

                match = pattern_ob.match(line)
                if match:
                    objpath, = match.groups()
                    continue

                match = pattern_pa.match(line)
                if match:
                    path, = match.groups()
                    continue

        # last id + shortname still hanging around
        if id and name:
            self._add_name(id, name, objpath=objpath, path=path)


    #wwnames.txt
    # An artificial list of names, with optionally an ID and descriptions, in various forms
    # - "(name) - (id)"
    # - "(name) = (id)"
    # - "(name)\t(id)"
    #
    # Name is always mandatory, and depending on ID:
    # - ID provided: accepts (some) non-valid names, also checks min value for ID (since this list
    #   may be built from software like strings2 it needs to weed out false positives).
    # - ID is 0: accepts (some) non-valid hashnames (Wwise does this for lang IDs like "English(US)"
    #   or busses like "Final Charge Up")
    # - no ID: only valid hashable names are accepted, but lines are split/processed
    def parse_lst(self, filename=None):
        if not filename:
            filename = self._make_filepath('wwnames.txt')
        self._parse_base(filename, self._parse_lst)

    def _parse_lst(self, infile):
        # list of processed names to quickly skips repeats
        processed = {}

        # catch: "name(thing) = id"
        pattern_1 = re.compile(r"^[\t]*([a-zA-Z_][a-zA-Z0-9()_ ]*)(\t| = | - )([0-9]+)[ ]*$")

        # catch "name"
        #pattern_2 = re.compile(r"^[\t]*([a-zA-Z_][a-zA-Z0-9_]*)[ ]*$")

        # catch and split non-useful (FNV) characters
        pattern_s1 = re.compile(r'[\t\n\r .<>,;.:{}\[\]()\'"$&/=!\\/#@+\^`´¨?|]')
        #pattern_s2 = re.compile(r'[?|]')

        for line in infile:
            match = pattern_1.match(line)
            if match:
                name, __, id = match.groups()

                if name in processed:
                    continue
                processed[name] = True

                forcehash = id == 0
                self._add_name(id, name, forcehash=forcehash, source=NameRow.NAME_SOURCE_EXTRA)
                continue

            #match = pattern_2.match(line)
            #if match:
            #    name, = match.groups()
            #
            #    if name in processed:
            #        continue
            #    processed[name] = True
            #
            #    self._add_name(None, name, onrepeat=Names.ONREPEAT_BEST, source=NameRow.NAME_SOURCE_EXTRA)
            #    continue

            # ignore comments
            if not line or line[0] == '#':
                continue
            # get sub-parts of a line and hash those, for scripts that have lines like "C_PlayMusic( bgm_01 )"
            # but we want "bgm_01" as the actual hashname, or XML like "<thing1 thing2='thing3'>"
            elems = pattern_s1.split(line)
            for elem in elems:
                #if pattern_s2.match(elem):
                #    continue
                self._parse_lst_elem(elem, processed)

        return

    def _parse_lst_elem(self, elem, processed):
        # not hashable
        if not elem or elem[0].isdigit() or len(elem) > 100:
            return
        if '|' in elem or '?' in elem:
            return

        # maybe could help
        if '-' in elem:
            elem = elem.replace('-', '_')

        # some elems in .exe have names like "bgm_%d" generated at runtime, simulate by making a bunch of names
        # (ex. MGR "bgm_r%03x_start", KOF13 "game_clear_%d")
        if '%' in elem:
            pos = elem.index('%')
            if pos == 0 or elem.count('%') > 1:
                return

            try:
                fmt = elem[pos+1]
                max = 2
                if fmt == '0':
                    max = int(elem[pos+2])
                    fmt = elem[pos+3]
                    if max > 4:
                        max = 4 #avoid too many names

                if fmt == 'd' or fmt == 'i' or fmt == 'u':
                    base = 10
                elif fmt == 'x' or fmt == 'X':
                    base = 16
                else:
                    return

                rng = range(0, pow(base, max), base)
                for i in rng:
                    elem_fmt = elem % (i)

                    if elem_fmt in processed:
                        continue
                    processed[elem_fmt] = True

                    self._add_name(None, elem_fmt, source=NameRow.NAME_SOURCE_EXTRA)
            except (ValueError, IndexError):
                pass #meh
            return

        # default
        if elem in processed:
            return
        processed[elem] = True

        self._add_name(None, elem, source=NameRow.NAME_SOURCE_EXTRA)

        return


    #wwnames.db3
    # An artificial SQLite DB of names. Not parsed, just prepared to be read on get_name
    #
    # Since a parser may load banks from multiple locations (base, langs, etc) other companion files
    # are read from those paths and added to this class' name list, but this DB is pre-generated and left
    # loaded to be used as-is for all banks so it only makes sense to load once from a single place
    def parse_db(self, filename=None):
        #if filename is None:
        #    filename = 'wwnames.db3' #work dir

        #don't reload DB
        if self._db:
            return
        self._db = SqliteHandler()
        self._db.open(filename)

    def close(self):
        if self._db:
            self._db.close()

    # saves loaded hashnames to .txt
    # (useful to check names when loading generic db/lst of names)
    def save_lst(self, name=None, save_all=False, save_companion=False, save_missing=False):
        if not name:
            name = 'banks'
        time = datetime.today().strftime('%Y%m%d%H%M%S')
        outname = 'wwnames-%s-%s.txt' % (name, time)

        logging.info("names: saving %s" % (outname))
        with open(outname, 'w', encoding='utf-8') as outfile:
            names = self._names.values()
            for row in names:
                #save hashnames only, as they can be safely shared between games
                if not row.hashname:
                    continue
                #save used names only, unless set to save all
                if not save_all and not row.hashname_used:
                    continue
                #save names not in xml/h/etc only, unless set to save extra
                if row.source != NameRow.NAME_SOURCE_EXTRA and not save_companion:
                    continue

                #logging.debug("names: using '%s'", row.hashname)
                outfile.write('%s\n' % (row.hashname))

                # log alts too (list should be cleaned up manually)
                for hashname in row.hashnames:
                    outfile.write('%s #alt\n' % (hashname))

            # write IDs that don't should have hashnames but don't
            if save_missing:
                for type in sorted(self._missing.keys()):
                    outfile.write('\n### MISSING %s NAMES\n' % (type.upper()))
                    ids = self._missing[type]
                    for id in ids:
                        outfile.write('# %s\n' % (id))

    # saves loaded hashnames to DB
    def save_db(self, save_all=False, save_companion=False):
        logging.info("names: saving db")
        if not self._db or not self._db.is_open():
            #force creation of BD if didn't exist
            #self._db.close() #not needed?
            self._db = SqliteHandler()
            self._db.open(None, preinit=True)

        self._db.save(self._names.values(), save_all=save_all, save_companion=save_companion)


    # banks could come from different paths
    def set_bankname(self, bankname):
        self._bankname = bankname

    # base path + name from a base filename (bank's folder+name)
    def _make_filepath(self, basename, basepath=None):
        if not basepath:
            basepath = self._bankname

        if basepath:
            pathname = os.path.dirname(basepath)
            if pathname:
                filename = os.path.join(pathname, basename)
            else:
                filename = basename
        else:
            filename = basename

        return filename


# #############################################################################

# helper containing a single name
class NameRow(object):
    __slots__ = ['id', 'name', 'type', 'hashname', 'hashnames', 'guidname', 'guidnames', 'objpath', 'path', 'hashname_used', 'source']

    NAME_SOURCE_COMPANION = 0 #XML/TXT/H
    NAME_SOURCE_EXTRA = 1 #LST/DB

    def __init__(self, id, hashname=None):
        self.id = id

        self.hashname = hashname
        self.guidname = None
        self.hashnames = [] #for list generation
        self.guidnames = [] #possible but useful?
        self.path = None
        self.objpath = None
        self.hashname_used = False
        self.source = None

    def _exists(self, name, list):
        if name.lower() in (listname.lower() for listname in list):
            return True
        return False

    def add_hashname(self, name):
        if not name:
            return
        if not self.hashname: #base
            self.hashname = name
        else:
            if name.lower() == self.hashname.lower():
                return
            if name.lower() in (hashname.lower() for hashname in self.hashnames):
                return
            self.hashnames.append(name) #alts

    def add_guidname(self, name):
        if not name:
            return
        if not self.guidname: #base
            self.guidname = name
        else:
            if name.lower() == self.guidname.lower():
                return
            if name.lower() in (guidname.lower() for guidname in self.guidnames):
                return
            self.guidnames.append(name) #alts

    def add_objpath(self, objpath):
        if not objpath:
            return
        self.objpath = objpath

    def add_path(self, path):
        if not path:
            return
        self.path = path


# ################################
# WARNING: BETA STUFF, MAY CHANGE
# ################################

class SqliteHandler(object):
    BATCH_COUNT = 50000     #more=higher memory, but much faster for huge (500000+) sets

    def __init__(self):
        self._cx = None

    def is_open(self):
        return self._cx

    def open(self, filename, preinit=False):
        if not filename:
            filename = 'wwnames.db3' #in work dir
        #if not filename:
        #    raise ValueError("filename not provided")

        basepath = filename
        workpath = os.path.dirname(sys.argv[0])
        workpath = os.path.join(workpath, filename)
        if os.path.isfile(basepath):
            path = basepath
        elif os.path.isfile(workpath):
            path = workpath
        else:
            path = None #no existing db3

        # connect() creates DB if file doesn't exists, allow only if flag is set
        if not path:
            if not preinit:
                logging.info("names: couldn't find %s name file", workpath)
                return
            path = filename

        #by default each thread needs its own cx (ex. viewer/server thread vs dumper/main thread),
        #but we don't really care since it's mostly read-only (could use some kinf od threadlocal?)
        self._cx = sqlite3.connect(path, check_same_thread=False)
        self._setup()

    def close(self):
        if not self._cx:
            return
        self._cx.close()

    def save(self, names, hashonly=False, save_all=False, save_companion=False):
        if not self._cx:
            return
        if not names:
            return

        cx = self._cx
        cur = cx.cursor()

        total = 0
        count = 0
        for row in names:
            #save hashnames only, as they can be safely shared between games
            if not row.hashname:
                continue
            #save used names only, unless set to save all
            if not save_all and not row.hashname_used:
                continue
            #save names not in xml/h/etc only, unless set to save extra
            if row.source != NameRow.NAME_SOURCE_EXTRA and not save_companion:
                continue


            params = (row.id, row.hashname)
            cur.execute("INSERT OR IGNORE INTO names(id, name) VALUES(?, ?)", params)
            #logging.debug("names: insert %s (%i)", row.hashname, cur.rowcount)

            count += cur.rowcount
            if count == self.BATCH_COUNT:
                total += count
                logging.info("names: %i saved...", total)
                cx.commit()
                count = 0

        total += count
        logging.info("names: total %i saved", total)
        cx.commit()


    def _to_namerow(self, row):
        #id = row['id']
        #name = row['name']
        id, name = row
        return NameRow(id, hashname=name)

    def select_by_id(self, id):
        if not self._cx:
            return
        #with closing(db.cursor()) as cursor: ???
        cur = self._cx.cursor()

        params = (id,)
        cur.execute("SELECT id, name FROM names WHERE id = ?", params)
        rows = cur.fetchall()
        for row in rows:
            return self._to_namerow(row)
        return None

    def select_by_id_fuzzy(self, id):
        if not self._cx:
            return
        cur = self._cx.cursor()

        #FNV hashes only change last byte when last char changes. We can use this property to get
        # close names (like "bgm1"=1189781958 / 0x46eaa1c6 and "bgm2"=1189781957 / 0x46eaa1c5)
        id = id & 0xFFFFFF00
        params = (id + 0, id + 256)
        cur.execute("SELECT id, name FROM names WHERE id >= ? AND id < ?", params)
        rows = cur.fetchall()
        for row in rows:
            return self._to_namerow(row)
        return None

    def _setup(self):
        cx = self._cx
        #init main table is not existing
        cur = cx.cursor()
        cur.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='%s'" % 'names')
        rows = cur.fetchall() #cur.rowcount is for updates
        if len(rows) >= 1:
            #migrate/etc
            return

        try:
            cur.execute("CREATE TABLE names(oid integer PRIMARY KEY, id integer, name text)") #, origin text, added date
            #cur.execute("CREATE INDEX index_names_id ON names(id)")
            cur.execute("CREATE UNIQUE INDEX index_names_id ON names(id)")

            #maybe should create a version table to handle schema changes
            cx.commit()
        finally:
            cx.rollback()


class Fnv(object):
    FNV_DICT = '0123456789abcdefghijklmnopqrstuvwxyz_'
    FNV_FORMAT = re.compile(r"^[a-z_][a-z0-9\_]*$")

    def is_hashable(self, lowname):
        return self.FNV_FORMAT.match(lowname)


    # Find actual name from a close name (same up to last char) using some fuzzy searching
    # ('bgm0' and 'bgm9' IDs only differ in the last byte, so it calcs 'bgm' + '0', '1'...)
    def unfuzzy_hashname(self, id, hashname):
        if not id or not hashname:
            return None

        namebytes = bytearray(hashname.lower(), 'UTF-8')
        basehash = self._get_hash(namebytes[:-1]) #up to last byte
        for c in self.FNV_DICT: #try each last char
            id_hash = self._get_partial_hash(basehash, ord(c))

            if id_hash == id:
                c = c.upper()
                for cs in hashname: #upper only if all base name is all upper
                    if cs.islower():
                       c = c.lower()
                       break

                hashname = hashname[:-1] + c
                return hashname
        # it's possible to reach here with incorrect (manually input) ids,
        # since not all 255 values are in FNV_DICT
        return None

    # Partial hashing for unfuzzy'ing.
    def _get_partial_hash(self, hash, value):
        hash = hash * 16777619 #FNV prime
        hash = hash ^ value #FNV xor
        hash = hash & 0xFFFFFFFF #python clamp
        return hash

    # Standard AK FNV-1 with 32-bit.
    def _get_hash(self, namebytes):
        hash = 2166136261 #FNV offset basis

        for i in range(len(namebytes)):
            hash = hash * 16777619 #FNV prime
            hash = hash ^ namebytes[i] #FNV xor
            hash = hash & 0xFFFFFFFF #python clamp
        return hash

    # Standard AK FNV-1 with 32-bit.
    def get_hash(self, lowname):
        namebytes = bytes(lowname, 'UTF-8')
        return self._get_hash(namebytes)
