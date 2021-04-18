import argparse, glob, logging, os, platform
from . import wparser, wprinter, wnames, wutil, wview, wgenerator
from . import wversion


class Cli(object):

    def __init__(self):
        pass

    def _parse(self):
        title = 'wwiser'
        version = ''
        if wversion.WWISER_VERSION:
            version += " " + wversion.WWISER_VERSION

        description = (
            "%s%s - Wwise .bnk parser by bnnm" % (title, version)
        )

        epilog = (
            "examples:\n"
            "  %(prog)s -d xsl bgm.bnk\n"
            "  - dumps bgm.bnk info to bgm.bnk.txt\n"
            "  %(prog)s -d txt init.bnk bgm.bnk -o banks\n"
            "  - loads multiple .bnk (like Wwise does) and dumps to banks.txt\n"
            "  %(prog)s *.bnk -v\n"
            "  - loads all .bnk in the dir and starts the viewer\n"
            "  %(prog)s BGM.bnk -g\n"
            "  - generates TXTP files from banks to use with vgmstream\n"
        )

        parser = argparse.ArgumentParser(prog="wwiser", description=description, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)
        # main options
        parser.add_argument('files', help="Files to get (wildcards work)", nargs='+')
        parser.add_argument('-m',  '--multi',           help="Treat files as multiple separate files", action='store_true')
        parser.add_argument('-d',  '--dump-type',       help="Set dump type: txt|xml|xsl|none|empty (default: auto)")
        parser.add_argument('-dn', '--dump-name',       help="Set dump filename (default: auto)")
        parser.add_argument('-l',  '--log',             help="Write info to wwiser log (has extra messages)", action='store_true')
        parser.add_argument('-v',  '--viewer',          help="Start the viewer", action='store_true')
        parser.add_argument('-vp', '--viewer-port',     help="Set the viewer port", default=wview.DEFAULT_PORT)
        parser.add_argument('-iv', '--ignore-version',  help="Ignore bank version check", action='store_true')
        # companion file options
        parser.add_argument('-nl', '--names-lst',           metavar='LST_NAME', help="Set wwnames.txt companion file (default: auto)")
        parser.add_argument('-nd', '--names-db',            metavar='DB_NAME',  help="Set wwnames.db3 companion file (default: auto)")
        # list options
        parser.add_argument('-sd', '--save-db',             help="Save/update wwnames.db3 with hashnames used in fields\n(needs dump set, or save-all)", action='store_true')
        parser.add_argument('-sl', '--save-lst',            help="Save .txt with hashnames actually used in fields\n(needs dump set)", action='store_true')
        parser.add_argument('-sm', '--save-missing',        help="Include in saved list of missing IDs\n(IDs that should have hashnames but weren't found)", action='store_true')
        parser.add_argument('-sc', '--save-companion',      help="Include in saved list companion names \n(loaded from companion XML/TXT/H, for a full list)", action='store_true')
        parser.add_argument('-sa', '--save-all',            help="Include all loaded names, rather than only used names", action='store_true')
        # txtp options
        parser.add_argument('-g',  '--txtp',                help="Generate TXTP", action='store_true')
        parser.add_argument('-gu', '--txtp-unused',         help="Generate TXTP for unused nodes too\n(try loading other banks first)", action='store_true')
        parser.add_argument('-go', '--txtp-outdir',         help="Set TXTP output dir (default: auto)")
        parser.add_argument('-gw', '--txtp-wemdir',         help="Set TXTP .wem dir (default: auto)")
        parser.add_argument('-gm', '--txtp-move',           help="Move all .wem referenced in loaded banks to wem dir", action='store_true')
        # txtp options related to filtering
        parser.add_argument('-gf', '--txtp-filter',         help="Set TXTP targets name/id/classname (default: auto)", nargs='+')
        parser.add_argument('-gfr','--txtp-filter-rest',    help="Generate rest of files after filtering\n(allows prioritizing some names then creating\nrestm to ensure won't be marked as dupes)", action='store_true')
        parser.add_argument('-gp', '--txtp-params',         help="Set TXTP parameters (default: auto)", nargs='*')
        parser.add_argument('-gd', '--txtp-dupes',          help="Generate TXTP duplicates\n(may create a lot of .txtp)", action='store_true')
        parser.add_argument('-gde','--txtp-dupes-exact',    help="Only consider dupes TXTP that are exactly the same\n(may create .txtp that sound 99%% the same)", action='store_true')
        parser.add_argument('-gbo','--txtp-bank-order',     help="Generate TXTP in bank order instead of names first\n(alters which .txtp are considered dupes)", action='store_true')
        # txtp options for extra behaviors
        parser.add_argument('-gwn','--txtp-wemname',        help="Add all .wem names to .txtp filename\n(may create too long filenames when many .wem are used)", action='store_true')
        parser.add_argument('-gbs','--txtp-bnkskip',        help="Treat internal (in .bnk) .wem as if external", action='store_true')
        parser.add_argument('-gbm','--txtp-bnkmark',        help="Mark .txtp that use internal .bnk (for reference)", action='store_true')
        parser.add_argument('-gae','--txtp-alt-exts',       help="Use TXTP alt extensions (.logg/lwav)", action='store_true')
        parser.add_argument('-gl', '--txtp-lang',           help="Mark .txtp and set .wem subdir per language\n(some games put voices/songs in 'English(US)' and such)", action='store_true')
        parser.add_argument('-gv', '--txtp-volume',         help="Set master TXTP volume, in percent or decibels\nexamples: 2.0=200%%, 0.5=50%%, -6dB=50%%, 6dB=200%%\n(negative dB needs equals: -gv=-6dB)")
        parser.add_argument('-gra','--txtp-random-all',     help="Make multiple .txtp per base 'random' group", action='store_true')
        parser.add_argument('-grm','--txtp-random-multi',   help="Force multiloops to be selectable like a 'random'\n(ex. make .txtp per layer in multiloops files)", action='store_true')
        parser.add_argument('-grf','--txtp-random-force',   help="Force base section to be selectable like a 'random'\n(ex. make .txtp per layer in all files)", action='store_true')
        parser.add_argument('-gwd','--txtp-write-delays',   help="Don't skip initial delay.\(some .txtp will start with some delay)", action='store_true')
        parser.add_argument('-gs', '--txtp-silence',        help="Silence by default parts that crossfade", action='store_true')
        parser.add_argument('-gt', '--txtp-tagsm3u',        help="Use shorter .txtp names and put full names in !tags.m3u", action='store_true')
        parser.add_argument('-gtl', '--txtp-tagsm3u-limit', help="Use shorter names + m3u by limiting original names to N chars", type=int)

        parser.add_argument('-gxnl','--txtp-x-noloops',     help="Extra: don't loop sounds", action='store_true')
        parser.add_argument('-gxnt','--txtp-x-notxtp',      help="Extra: don't save .txtp", action='store_true')
        parser.add_argument('-gxni','--txtp-x-nameid',      help="Extra: add ID to generic names", action='store_true')

        return parser.parse_args()


    def _is_filename_ok(self, filenames, filename):
        if not os.path.isfile(filename):
            return False
        if filename.upper() in (filename.upper() for filename in filenames):
            return False
        if filename.endswith(".py"):
            return False
        return True


    def start(self):
        wutil.setup_cli_logging()
        args = self._parse()
        if args.log:
            wutil.setup_file_logging()

        title = 'wwiser'
        if wversion.WWISER_VERSION:
            title += " " + wversion.WWISER_VERSION
        logging.info("%s (python %s)", title, platform.python_version())


        #get expanded list
        filenames = []
        for file in args.files:
            # manually test first, as glob expands "[...]" inside paths
            if os.path.isfile(file):
                if not self._is_filename_ok(filenames, file):
                    continue
                filenames.append(file)
            else:
                glob_files = glob.glob(file)
                for glob_file in glob_files:
                    if not self._is_filename_ok(filenames, glob_file):
                        continue
                    filenames.append(glob_file)

        if not filenames:
            logging.info("no valid files found")
            return

        if args.multi:
            for filename in filenames:
                self._execute(args, [filename])
        else:
            self._execute(args, filenames)

        logging.info("(done)")


    def _execute(self, args, filenames):

        # process banks
        parser = wparser.Parser(ignore_version=args.ignore_version)
        parser.parse_banks(filenames)
        banks = parser.get_banks()

        # load names
        names = wnames.Names()
        names.parse_files(banks, parser.get_filenames(), lst=args.names_lst, db=args.names_db)
        parser.set_names(names)

        # dump files
        dump_name = args.dump_name
        if not dump_name:
            if len(filenames) == 1:
                dump_name = filenames[0]
            else:
                dump_name = 'banks'

        # default dump type
        if args.dump_type is None:
            if args.save_lst:
                 #forces all names without making a file
                args.dump_type = wprinter.TYPE_EMPTY
            elif args.txtp or args.viewer:
                # not very useful for txtp/viewer
                args.dump_type = wprinter.TYPE_NONE
            else:
                # default without other flags
                args.dump_type = wprinter.TYPE_XSL
        printer = wprinter.Printer(banks, args.dump_type, dump_name)
        printer.dump()

        # start viewer
        if args.viewer:
            viewer = wview.Viewer(parser)

            logging.info("(stop viewer with CTRL+C)")
            viewer.start(port=args.viewer_port)
            #left open until manually stopped
            viewer.stop()

        # generate txtp
        if args.txtp:
            generator = wgenerator.Generator(banks)
            generator.set_generate_unused(args.txtp_unused)
            generator.set_filter(args.txtp_filter)
            generator.set_filter_rest(args.txtp_filter_rest)
            generator.set_params(args.txtp_params)
            generator.set_dupes(args.txtp_dupes)
            generator.set_dupes_exact(args.txtp_dupes_exact)
            generator.set_bank_order(args.txtp_bank_order)

            generator.set_outdir(args.txtp_outdir)
            generator.set_wemdir(args.txtp_wemdir)
            generator.set_move(args.txtp_move)
            generator.set_wemnames(args.txtp_wemname)
            generator.set_bnkskip(args.txtp_bnkskip)
            generator.set_bnkmark(args.txtp_bnkmark)

            generator.set_alt_exts(args.txtp_alt_exts)
            generator.set_lang(args.txtp_lang)
            generator.set_volume(args.txtp_volume)
            generator.set_random_all(args.txtp_random_all)
            generator.set_random_multi(args.txtp_random_multi)
            generator.set_random_force(args.txtp_random_force)
            generator.set_write_delays(args.txtp_write_delays)
            generator.set_silence(args.txtp_silence)
            generator.set_tagsm3u(args.txtp_tagsm3u)
            generator.set_tagsm3u_limit(args.txtp_tagsm3u_limit)

            generator.set_x_noloops(args.txtp_x_noloops)
            generator.set_x_notxtp(args.txtp_x_notxtp)
            generator.set_x_nameid(args.txtp_x_nameid)

            generator.generate()


        # db manipulation
        if args.dump_type == wprinter.TYPE_NONE and (args.save_lst or args.save_db):
            logging.info("dump set to none, may not save all names")
        if args.save_lst:
            names.save_lst(name=dump_name, save_all=args.save_all, save_companion=args.save_companion, save_missing=args.save_missing)
        if args.save_db:
            names.save_db(save_all=args.save_all, save_companion=args.save_companion)
        names.close() #in case DB was open

        #try:
            #import objgraph
            #objgraph.show_most_common_types()

            #from guppy import hpy; h=hpy()
            #h.heap()

            #from . import wmodel
            #import sys
            #print("NodeElement: %x" % sys.getsizeof(wmodel.NodeElement(None, 'test')))
            #getsizeof(wmodel.NodeElement()), getsizeof(Wrong())
        #except:
            #pass
