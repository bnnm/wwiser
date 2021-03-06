import logging, re, os, os.path, sys, sqlite3
from datetime import datetime
from . import wfnv


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
#
# Companion files are created by the editor depending on the "project settings" options.
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
        self._fnv = wfnv.Fnv()
        self._disable_fuzzy = False


    def set_gamename(self, gamename):
        self._gamename = gamename #path

    def _mark_used(self, row):
        #if row.hashname_used:
        #    return
        row.hashname_used = True

        # log this first time it's marked as used
        if not row.multiple_marked and row.hashnames:
            old = row.hashname
            new = row.hashnames[0]
            # could show more but not too interesting
            logging.info("names: alt hashnames (using old), old=%s vs new=%s" % (old, new))
            row.multiple_marked = True


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
                self._mark_used(row)
            return row

        # hashnames not allowed
        if no_hash:
            # next tests only find ids with hashnames
            return None

        # on list with a close ID
        row_fz = None
        if not self._disable_fuzzy:
            id_fz = id & 0xFFFFFF00
            row_fz = self._names_fuzzy.get(id_fz)
        if row_fz and row_fz.hashname:
            hashname_uf = self._fnv.unfuzzy_hashname(id, row_fz.hashname)
            row = self._add_name(id, hashname_uf, source=NameRow.NAME_SOURCE_EXTRA)
            if row:
                self._mark_used(row)
                return row

        if not self._db:
            return None

        # on db (add to names for easier access and saving list of wwnames)
        # when using db always set extended hash to allow bus names (and maybe guidnames?)
        row_db = self._db.select_by_id(id)
        if row_db:
            row = self._add_name(id, row_db.hashname, source=NameRow.NAME_SOURCE_EXTRA, exhash=True)
            if row:
                self._mark_used(row)
                return row

        # on db with a close ID
        row_df = None
        if not self._disable_fuzzy:
            row_df = self._db.select_by_id_fuzzy(id)
        if row_df and row_df.hashname:
            hashname_uf = self._fnv.unfuzzy_hashname(id, row_df.hashname)
            row = self._add_name(id, hashname_uf, source=NameRow.NAME_SOURCE_EXTRA, exhash=True)
            if row:
                self._mark_used(row)
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
    def _add_name(self, id, name, objpath=None, path=None, onrepeat=ONREPEAT_INCLUDE, exhash=False, source=None):
        if name:
            name = name.strip()
        if objpath:
            objpath = objpath.strip()
        if path:
            path = path.strip()
        if not name: #after strip
            return None

        lowname = name.lower()
        hashable = self._fnv.is_hashable(lowname)
        extended = False
        if not hashable and exhash:
            hashable = self._fnv.is_hashable_extended(lowname)
            extended = hashable

        if not id and not hashable:
            return None
        id_hash = self._fnv.get_hash_lw(lowname)

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
                    #logging.info("names: alt hashname (using old), old=%s vs new=%s" % (row.hashname, name))
                    #return None #allow to add as alt, logged once used
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
            row.add_hashname(name, extended=extended)
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

    # *************************************************************************

    def parse_files(self, banks, filenames, xml=None, txt=None, h=None, lst=None, db=None, json=None):
        if not filenames:
            return
        logging.info("names: loading names")

        # add banks names (doubles as hashnames), first since it looks a bit nicer in list output
        for bank in banks:
            bankname = bank.get_root().get_bankname()
            self._add_name(None, bankname, source=NameRow.NAME_SOURCE_EXTRA)

        # parse files for each single bank
        for filename in filenames:
            # update current bank name (in case of mixed bank dirs; repeats aren't parsed again)
            self.set_bankname(filename)

            # from more to less common/useful
            self.parse_xml(xml)
            self.parse_xml_bnk(xml)
            self.parse_txt_bnk(txt)
            self.parse_json(json)
            self.parse_json_bnk(json)

        # banks may store some extra hashname strings (rarely)
        for bank in banks:
            strings = bank.get_root().get_strings()
            for string in strings:
                self._add_name(None, string, source=NameRow.NAME_SOURCE_EXTRA)

        # parse .h (names in CAPS so less priority)
        for filename in filenames:
            self.set_bankname(filename)
            self.parse_h(h)

        # extra files, after other banks or priority when generating some missing lists and stuff is off
        for filename in filenames:
            self.set_bankname(filename)

            self.parse_lst(lst)

        # current folder just in case
        self.set_bankname(None)
        self.parse_lst(lst)

        # program folder also just in case
        self.set_bankname(sys.argv[0])
        self.parse_lst(lst)

        # automatically from program folder, only one db3 is allowed
        self.parse_db(db)

        self.set_bankname(None)

        logging.info("names: done")


    def _parse_base(self, filename, callback, reverse_encoding=False):
        encodings = ['utf-8', 'iso-8859-1']
        if reverse_encoding:
            encodings.reverse()
        try:
            if filename in self._loaded_banknames:
                #logging.debug("names: ignoring already loaded file " + filename)
                return

            #logging.debug("names: testing " + filename)
            if not os.path.isfile(filename):
                return
            logging.info("names: loading " + filename)

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


    # Wwise_IDs.h ('header file')
    #
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


    # (bankname).txt ('bank content TXT')
    #
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
    # Paths go after 3 tabs (except for wem paths), while other sections use 1 tab.
    # "State" (not "State Groups")'s path is actually the state group (could be separated)
    # Wem names can be anything, so we want to capture any text
    #
    # Encoding on Windows is cp-1252 (has 0xA9=copyright), maybe Linux/Mac would use
    # UTF-8, but those symbols seem only used in comments so shouldn't matter too much
    # (other than Python throwing exceptions on unknown chars). Wwise lets you choose
    # between "ANSI" and "Unicode".
    def parse_txt_bnk(self, filename=None):
        if not filename:
            filename = os.path.splitext(self._bankname)[0] + '.txt'
        self._parse_base(filename, self._parse_txt, reverse_encoding=True)

    def _parse_txt(self, infile):
        #catch: "	1234155799	Play_Thing			\Default Work Unit\Play_Thing	" (with path being optional)
        # must also catch buses like "3D-Submix_Bus"
        #pattern_ph = re.compile("^\t([0-9]+)\t([a-zA-Z_][a-zA-Z0-9_ ]*)(\t\t\t([^\t]+))?.*")
        #pattern_ph = re.compile(r"^\t([0-9]+)\t([^\t]+)(\t\t*?\t*?([^\t]+))?.*")
        bus_starts = ['Bus', 'Audio Bus', 'Auxiliary Bus']
        pattern_ph = re.compile(r"^\t([0-9]+)\t([^\t]+)[\t ]*([^\t]*)[\t ]*([^\t]*)")

        bus_hash = False
        for line in infile:
            if not line:
                continue
            # reset+test bus flag in new sectiona
            if not line.startswith('\t'):
                bus_hash = False
                for bus_start in bus_starts:
                    if line.startswith(bus_start):
                        bus_hash = True #next names will be buses, and may use extended hash
                        break

            match = pattern_ph.match(line)
            if match:
                id, name, info1, info2 = match.groups()
                path, objpath = self._parse_txt_info(info1, info2)

                self._add_name(id, name, objpath=objpath, path=path, exhash=bus_hash)

    # After name there can be comments, paths or objpaths. Not very consistent so do some autodetection
    def _parse_txt_info(self, info1, info2):
        path = ''
        objpath = ''

        if self._is_objpath(info1):
            objpath = info1
        elif self._is_path(info1):
            path = info1

        if self._is_objpath(info2):
            objpath = info2
        elif self._is_path(info2):
            path = info2

        return (path, objpath)

    def _is_objpath(self, info):
        return info and (info.startswith('\\') or info.startswith('//'))

    def _is_path(self, info):
        return info and len(info) > 2 and info[1] == ':' and info[2] == '\\'


    # SoundbanksInfo.xml ('XML metadata')
    # (bankname).xml
    #
    # An XML with info about bank objects. Main targets are:
    # - <(object) Id="(id)" Name="(name)" ...
    # - <(object) Id="(id)" ...>\n ...  <ShortName>(name)</ShortName> <Path>(path)</Path>...
    # Names are hashnames, while ShortNames/Paths may be anything (including UTF-8), usually
    # Paths is the real file ("sfx/file.wav"), while ShortName is may be shared (like multi-lang
    # .wem with same ShortName but different Paths) and can be a hashname. Other attrs include
    # ObjectPath (not too useful, see .txt info). Some tags are just IDs
    # links without name though.
    #
    # The XML can be big (+20MB) and since we don't need all details and just id/names it can be
    # parsed as simple text to increase performance.
    # 
    # Devs may generate one .xml per bnk instead but this is much less common
    def parse_xml(self, filename=None):
        if not filename:
            filename = self._make_filepath('SoundbanksInfo.xml')
        self._parse_base(filename, self._parse_xml)

    def parse_xml_bnk(self, filename=None):
        if not filename:
            filename = os.path.splitext(self._bankname)[0] + '.xml'
        self._parse_base(filename, self._parse_xml)

    def _parse_xml(self, infile):
        #catch: "	<Thing Id="12345" Name="Play_Thing" ObjectPath="\Default Work Unit\Play_Thing">"
        pattern_in = re.compile(r"^.*<.+ Id=[\"]([0-9]+)[\"] .*Name=[\"]([a-zA-Z0-9_]+)[\"](.* ObjectPath=[\"](.+?)[\"])?.+")
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


    # SoundbanksInfo.json ('JSON metadata')
    # (bankname).json
    #
    # A json equivalent to SoundbanksInfo.xml and (bankname).txt, added in ~2020, format roughly being:
    # "(type)": [
    #    { id: ..., field: ... }
    # ],
    # "(type)": [
    # ....
    #
    # Like other files, to avoid loading the (often massive) .json and handling schema
    # changes, just find an "id" then get all possible fields until next "id".
    def parse_json(self, filename=None):
        if not filename:
            filename = self._make_filepath('SoundbanksInfo.json')
        self._parse_base(filename, self._parse_json)

    def parse_json_bnk(self, filename=None):
        if not filename:
            filename = os.path.splitext(self._bankname)[0] + '.json'
        self._parse_base(filename, self._parse_json)

    def _parse_json(self, infile):
        #catch: '	"Id": "12345" '
        pattern_id = re.compile(r"^[ \t]+[\"]Id[\"]: [\"](.+?)[\"][, \t]*")
        #catch: '	"(field)": "(value)" '
        pattern_fv = re.compile(r"^[ \t]+[\"](.+)[\"]: [\"](.+?)[\"][, \t]*")

        id = name = objpath = path = None
        for line in infile:
            # try id (may change multiple times)
            match = pattern_id.match(line)
            if match:
                # prev id + name still hanging around
                if id and name:
                    #print("add", id, name, objpath, path)
                    self._add_name(id, name, objpath=objpath, path=path)

                id = name = objpath = path = None
                id, = match.groups()
                continue

            # If id was found (in the above match or a previous one) try parts
            # This assumes an id is followed by names, could get fooled in some cases.
            if id:
                match = pattern_fv.match(line)
                if match:
                    field, value = match.groups()
                    if   field == 'Name':
                        name = value
                    elif field == 'ShortName': #treated as name, will be identified as guidname when added
                        name = value
                    elif field == 'ObjectPath':
                        objpath = value
                    elif field == 'Path':
                        path = value
                    continue

        # last id + name still hanging around
        if id and name:
            self._add_name(id, name, objpath=objpath, path=path)


    # wwnames.txt
    #
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

        # catch: "name(thing) = id" (ex. "8bit", "English(US)", "3D-Submix_Bus")
        pattern_1 = re.compile(r"^[\t]*([a-zA-Z_0-9][a-zA-Z0-9_()\- ]*)( = )([0-9]+)[ ]*$")

        # catch "name"
        #pattern_2 = re.compile(r"^[\t]*([a-zA-Z_][a-zA-Z0-9_]*)[ ]*$")

        # catch and split non-useful (FNV) characters
        pattern_s1 = re.compile(r'[\t\n\r .<>,;.:{}\[\]()\'"$&/=!\\/#@+\^`´¨?|~]')
        #pattern_s2 = re.compile(r'[?|]')

        for line in infile:
            # ignore comments
            if not line:
                continue
            if line[0] == '#':
                # special flag for complete wwnames that need no fuzzies
                if line.startswith('#@nofuzzy'):
                    self._disable_fuzzy = True
                continue

            match = pattern_1.match(line)
            if match:
                name, __, id = match.groups()
                if name in processed:
                    continue

                #special meaning of "extended hash" (for objects like buses)
                if id == '0':
                    processed[name] = True
                    self._add_name(None, name, exhash=True, source=NameRow.NAME_SOURCE_EXTRA)
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

                    self._parse_lst_elem_add(elem_fmt, processed)
            except (ValueError, IndexError):
                pass #meh
            return

        # some odd game has names ending with _ but shouldn't
        if elem.endswith("_"):
            elem_cut = elem[:-1]
            self._parse_lst_elem_add(elem_cut, processed)

        # it's common to use vars that start with _ but maybe will get a few extra names
        if elem.startswith("_"):
            elem_cut = elem[1:]
            self._parse_lst_elem_add(elem_cut, processed)

        # default
        self._parse_lst_elem_add(elem, processed)
        return

    def _parse_lst_elem_add(self, elem, processed):
        if elem in processed:
            return
        processed[elem] = True

        self._add_name(None, elem, source=NameRow.NAME_SOURCE_EXTRA)


    # wwnames.db3
    #
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
        else:
            name = os.path.basename(name)
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
                extended = ''
                if row.extended:
                    extended = ' = 0' #allow names with special chars
                outfile.write('%s%s\n' % (row.hashname, extended))

                # log alts too (list should be cleaned up manually)
                for hashname in row.hashnames:
                    if extended: #todo improve
                        outfile.write('#alt\n')
                        outfile.write('%s%s\n' % (row.hashname, extended))
                    else:
                        outfile.write('%s #alt\n' % (hashname)) #todo not read ok?

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
    __slots__ = ['id', 'name', 'type', 'hashname', 'hashnames', 'guidname', 'guidnames', 'objpath', 'path', 'hashname_used', 'multiple_marked', 'source', 'extended']

    NAME_SOURCE_COMPANION = 0 #XML/TXT/H
    NAME_SOURCE_EXTRA = 1 #LST/DB

    def __init__(self, id, hashname=None):
        self.id = id

        self.hashname = hashname
        self.guidname = None
        self.hashnames = [] #for list generation (contains only extra names, main is in "hashname")
        self.guidnames = [] #possible but useful?
        self.path = None
        self.objpath = None
        self.hashname_used = False
        self.multiple_marked = False
        self.source = None
        self.extended = False

    def _exists(self, name, list):
        if name.lower() in (listname.lower() for listname in list):
            return True
        return False

    def add_hashname(self, name, extended=False):
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
        self.extended = extended

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
        logging.info("names: loading %s", filename)

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
