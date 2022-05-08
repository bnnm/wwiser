import logging, os, os.path, sys, sqlite3
from .wnamerow import NameRow

# wwnames.db3 database handler
# This is meant to be a common names database (like a default wwnames.txt)
# However since wwise's hash is too simple and has many collisions, this isn't that useful.

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
