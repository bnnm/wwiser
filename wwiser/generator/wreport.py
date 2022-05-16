import logging


class Report(object):

    def __init__(self, generator):
        self._generator = generator

    def report(self):
        gen = self._generator
        reb = gen._builder
        txc = gen._txtpcache
        mdi = gen._txtpcache.mediaindex
        stats = gen._txtpcache.stats

        if reb.has_unused() and not gen._generate_unused:
            logging.info("generator: NOTICE! possibly unused audio? (find+load more banks?)")
            logging.info("*** set 'generate unused' option to include, may not create anything")

        if mdi.get_missing_media():
            missing = len(mdi.get_missing_media())
            logging.info("generator: WARNING! missing %s memory audio (load more banks?)", missing)

        if reb.get_missing_nodes_loaded():
            missing = len(reb.get_missing_nodes_loaded())
            logging.info("generator: WARNING! missing %s Wwise objects in loaded banks (ignore?)", missing)

        if reb.get_missing_nodes_others():
            missing = len(reb.get_missing_nodes_others())
            logging.info("generator: WARNING! missing %s Wwise objects in other banks (load?)", missing)
            for bankinfo in reb.get_missing_banks():
                logging.info("- %s.bnk" % (bankinfo))

        if reb.get_missing_nodes_unknown():
            missing = len(reb.get_missing_nodes_unknown())
            logging.info("generator: WARNING! missing %s Wwise objects in unknown banks (load/ignore?)", missing)

        if reb.get_multiple_nodes():
            missing = len(reb.get_multiple_nodes())
            logging.info("generator: WARNING! repeated %s Wwise objects in multiple banks (load less?)", missing)

        if not stats.created:
            logging.info("generator: WARNING! no .txtp were created (find+load banks with events?)")

        if reb.get_transition_objects():
            logging.info("generator: REPORT! transition object in playlists")
        if reb.get_unknown_props():
            logging.info("generator: REPORT! unknown properties in some objects")
            for prop in reb.get_unknown_props():
                logging.info("- %s" % (prop))

        if stats.trims:
            logging.info("generator: NOTICE! trimmed %s long filenames (use shorter dirs?)", stats.trims)
            logging.info("*** set 'tags.m3u' option for shorter names + tag file with full names")

        if stats.multitrack and not gen._default_gsparams:
            logging.info("generator: multitracks detected (ignore, may generate in future versions)")

        dir = txc.get_txtp_dir()
        if not dir:
            dir = '.'

        if stats.streams and not gen._move:
            logging.info("generator: some .txtp (%s) use streams, move to %s", stats.streams, dir)
        if stats.internals and not txc.bnkskip:
            logging.info("generator: some .txtp (%s) use .bnk, move to %s", stats.internals, dir)
            for bankname in txc.stats.get_used_banks():
                logging.info("- %s", bankname)

        #logging.info("generator: done")
        line = "created %i" % stats.created
        if stats.duplicates:
            line += ", %i duplicates" % stats.duplicates
        if gen._generate_unused:
            line += ", unused %i" % stats.unused
        logging.info("generator: done (%s)", line)
