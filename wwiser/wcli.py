import sys, argparse, glob, logging, os, platform, shlex

from . import wversion, wlogs, wtests
from .names import wnames
from .parser import wparser
from .viewer import wdumper, wview
from .generator import wgenerator, wtags, wlocator
from .tools import wcleaner
from . import wfnv


class Cli(object):

    def __init__(self):
        self._parser = None
        return

    def _parse_init(self):
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
            "  %(prog)s -d txt init.bnk bgm.bnk -dn banks\n"
            "  - loads multiple .bnk (like Wwise does) and dumps to banks.txt\n"
            "  %(prog)s *.bnk -v\n"
            "  - loads all .bnk in the dir and starts the viewer\n"
            "  %(prog)s BGM.bnk -g\n"
            "  - generates TXTP files from banks to use with vgmstream\n"
        )

        parser = argparse.ArgumentParser(prog="wwiser", description=description, epilog=epilog, formatter_class=argparse.RawTextHelpFormatter)

        p = parser.add_argument_group('base options')
        p.add_argument('files',                         help="Files to get (wildcards work)", nargs='*')
        p.add_argument('-m',  '--multi',                help="Treat files as multiple separate files", action='store_true')
        p.add_argument('-r',  '--recursive',            help="Load banks recursively (use with wildcards like **/*.bnk)", action='store_true')
        p.add_argument('-c',  '--config',               help="Set config text file\nAllows same CLI options but in a text file\n(may split commands into multiple lines)\n(write '#@new' to start a new process in the same file)")
        p.add_argument('-d',  '--dump-type',            help="Set dump type: txt|xml|xsl|xsl_s|xsl_xs|none (default: auto)", metavar='TYPE')
        p.add_argument('-dn', '--dump-name',            help="Set dump filename (default: auto)", metavar='NAME')
        p.add_argument('-l',  '--log',                  help="Write info to wwiser log (has extra messages)", action='store_true')
        p.add_argument('-v',  '--viewer',               help="Start the viewer", action='store_true')
        p.add_argument('-vp', '--viewer-port',          help="Set the viewer port", metavar='PORT', default=wview.DEFAULT_PORT)
        #p.add_argument('-iv', '--ignore-version',      help="Ignore bank version check", action='store_true')
        p.add_argument('-sl', '--save-lst',             help="Clean wwnames.txt and include missing hashnames\n(needs dump set)", action='store_true')
        p.add_argument('-br', '--bank-repeat',          help="Override repeated banks handling:\n  manual / first / last / smallest / biggest / biggest+last")

        p = parser.add_argument_group('txtp options')
        p.add_argument('-g',  '--txtp',                 help="Generate TXTP", action='store_true')
        p.add_argument('-gu', '--txtp-unused',          help="Generate TXTP for unused nodes too\n(try loading other banks first)", action='store_true')
        p.add_argument('-go', '--txtp-outdir',          help="Set TXTP output dir (default: auto)\nadd '/*' at the end to put txtp in subfolders per bank")
        p.add_argument('-gw', '--txtp-wemdir',          help="Set TXTP .wem dir (default: auto)", default='*')
        p.add_argument('-gv', '--txtp-volume',          help="Set master TXTP volume, in percent or decibels\nexamples: *=auto, 2.0=200%%, 0.5=50%%, -6dB=50%%, 6dB=200%%\n(negative dB needs equals: -gv=-6dB)", default='*')

        p = parser.add_argument_group('txtp Wwise state options')
        p.add_argument('-gp',   '--txtp-params',            help="Set TXTP gamesync list (default: auto)", metavar='ITEMS', nargs='*')
        p.add_argument('-gs',   '--txtp-statechunks',       help="Set TXTP statechunks list (default: auto)", metavar='ITEMS', nargs='*')
        p.add_argument('-gg',   '--txtp-gamevars',          help="Set TXTP game parameter list (default: auto)", metavar='ITEMS', nargs='*')
        p.add_argument('-gssd', '--txtp-statechunks-sd',    help="Skip default statechunk (default: auto)", action='store_true')
        p.add_argument('-gssu', '--txtp-statechunks-su',    help="Skip unreachable statechunks (default: auto)", action='store_true')

        p = parser.add_argument_group('txtp filtering options')
        p.add_argument('-gf', '--txtp-filter',          help="List of allowed event/id/classname/bnk/etc", metavar='ITEMS', nargs='+')
        p.add_argument('-gfr','--txtp-filter-rest',     help="Generate rest of files after filtering\n(allows prioritizing names in filter then creating\nrest, altering dupe order)", action='store_true')
        p.add_argument('-gfn','--txtp-filter-normal',   help="Skip normal files\n(allows writting unused only)", action='store_true')
        p.add_argument('-gfu','--txtp-filter-unused',   help="Skip unused files\n(for testing)", action='store_true')
        p.add_argument('-gd', '--txtp-dupes',           help="Generate TXTP duplicates\n(may create a lot of .txtp)", action='store_true')
        p.add_argument('-gde','--txtp-dupes-exact',     help="Only consider dupes TXTP that are exactly the same\n(may create .txtp that sound 99%% the same)", action='store_true')
        p.add_argument('-gbo','--txtp-bank-order',      help="Generate TXTP in bank order instead of names first\n(alters which .txtp are considered dupes)", action='store_true')
        p.add_argument('-gr', '--txtp-renames',         help="Set TXTP renames in the form of text-in:text-out", metavar='ITEMS', nargs='+')

        p = parser.add_argument_group('txtp misc options')
        p.add_argument('-gnw','--txtp-name-wems',       help="Add all .wem names to .txtp name\n(may create too long filenames when many .wem are used)", action='store_true')
        p.add_argument('-gnv','--txtp-name-vars',       help="Write ignored variables in .txtp name\n(filenames may look more orderly in some cases)", action='store_true')
        p.add_argument('-gbs','--txtp-bnkskip',         help="Treat internal (in .bnk) .wem as if external", action='store_true')
        p.add_argument('-gbm','--txtp-bnkmark',         help="Mark .txtp that use internal .bnk (for reference)", action='store_true')
        p.add_argument('-gae','--txtp-alt-exts',        help="Use TXTP alt extensions (.logg/lwav)", action='store_true')
        p.add_argument('-gl', '--txtp-lang',            help="Set current language(s) and mark localized .txtp with it\nUseful when loading bnks in different folders so other\nlangs are skipped (use 'SFX' to skip localized banks)\nAllows full names like 'English(US)' or shorhands like 'en'", metavar='LANGS', nargs='*')
        p.add_argument('-gra','--txtp-random-all',      help="Make multiple .txtp per base 'random' group", action='store_true')
        p.add_argument('-grm','--txtp-random-multi',    help="Force multiloops to be selectable like a 'random'\n(ex. make .txtp per layer in multiloops files)", action='store_true')
        p.add_argument('-grf','--txtp-random-force',    help="Force base section to be selectable like a 'random'\n(ex. make .txtp per layer in all files)", action='store_true')
        p.add_argument('-gwd','--txtp-write-delays',    help="Don't skip initial delay.\n(some .txtp will start with some delay)", action='store_true')

        p = parser.add_argument_group('other options')
        p.add_argument('-te', '--tags-event',           help="Use shorter .txtp names and put full names in !tags.m3u", action='store_true')
        p.add_argument('-tl', '--tags-limit',           help="Use shorter names + m3u by limiting original names to N", metavar='LIMIT', type=int)
        p.add_argument('-tw', '--tags-wem',             help="Make !tags.m3u for .wem in folder", action='store_true')
        p.add_argument('-ta', '--tags-add',             help="Add to existing !tags.m3u instead of overwritting", action='store_true')
        p.add_argument('-fc', '--file-cleaner',         help="Move .wem/bnk not used in .txtp to unused folder", action='store_true')

        p = parser.add_argument_group('extra options (for testing)')
        p.add_argument('-nl', '--names-lst',            help="Set wwnames.txt companion file (default: auto)", metavar='NAME')
        p.add_argument('-nd', '--names-db',             help="Set wwnames.db3 companion file (default: auto)", metavar='NAME')
        p.add_argument('-sd', '--save-db',              help="Save/update wwnames.db3 with hashnames used in fields\n(needs dump set, or save-all)", action='store_true')
        p.add_argument('-gm', '--txtp-move',            help="Move all .wem referenced in loaded banks to wem dir", action='store_true')

        p.add_argument('-gxs', '--txtp-x-silence',     help="Silence by default parts that crossfade", action='store_true')
        p.add_argument('-gxif','--txtp-x-include-fx',  help="Apply FX volumes", action='store_true')
        p.add_argument('-gxpp','--txtp-x-prefilter-paths',  help="Prefilter unreachable paths (for games with huge trees)", action='store_true')
        p.add_argument('-gxnl','--txtp-x-noloops',     help="Extra: don't loop sounds", action='store_true')
        p.add_argument('-gxni','--txtp-x-nameid',      help="Extra: add ID to generic names", action='store_true')
        p.add_argument('-x','--tests',                 help="Extra: debug", action='store_true')

        self._parser = parser

    # read config file's lines to make one (or many) configs, and pass to argparse
    def _handle_config(self, args):
        config_name = args.config
        if config_name == '*':
            config_name = 'wwconfig.txt'

        defaults = sys.argv[1:]
        try:
            defaults.remove(config_name)
        except ValueError:
            pass

        configs = []

        current = []
        current += defaults
        configs.append(current)
        empty = True

        with open(config_name, 'r', encoding='utf-8-sig') as f:
            for line in f:
                line = line.strip()
                line_command = line.split(' ')[0]

                # start a new config 'chunk' (useful to set different filters/config per bank)
                if line_command == '#@new' and not empty:
                    current = []
                    current += defaults
                    configs.append(current)
                    empty = True
                    continue

                # stop config (useful quick testing of new configs)
                if line_command == '#@break':
                    break

                if line.startswith('#'):
                    continue

                #parts = line.split(" ") #splits between quotes: "bla blah"
                parts = shlex.split(line) #doesn't split between quotes
                for part in parts:
                    #part = part.strip() #shlex strips if outside quotes, otherwise allows them
                    if part:
                        current.append(part)
                        empty = False

        # reset config + parse parse config args (per config chunk)
        for config in configs:
            if len(config) == 0:
                continue
            args = self._parser.parse_args(config)
            self._run(args)

        return

    def start(self):
        wlogs.setup_cli_logging()
        self._parse_init()

        args = self._parser.parse_args()

        # detect special filename to simplify config
        if len(args.files) == 1 and 'wwconfig' in args.files[0]:
           args.config = args.files[0]
           args.files = []

        if args.config:
            self._handle_config(args)
        else:
            self._run(args)


    def _is_filename_ok(self, filenames, filename):
        if not os.path.isfile(filename):
            return False
        if filename.upper() in (filename.upper() for filename in filenames):
            return False
        if filename.endswith(".py"):
            return False
        return True

    def _add_files(self, files, filenames):
        for file in files:
            if not self._is_filename_ok(filenames, file):
                continue
            filenames.append(file)

    def _run(self, args):
        if args.log:
            wlogs.setup_file_logging()

        title = 'wwiser'
        if wversion.WWISER_VERSION:
            title += " " + wversion.WWISER_VERSION
        logging.info("%s (python %s)", title, platform.python_version())


        # get expanded list
        fnv = wfnv.Fnv()
        filenames = []
        for file in args.files:
            # existing file: manually test as glob expands "[...]" inside paths
            if os.path.isfile(file):
                self._add_files([file], filenames)
                continue

            # wildcards: try globbed
            if args.recursive:
                if '**' not in file:
                    file = '**/' + file
                glob_files = glob.glob(file, recursive=True)
            else:
                glob_files = glob.glob(file)
            self._add_files(glob_files, filenames)
            if glob_files:
                continue

            # non-existing: to simplify using non-renamed banks, try hashname to id (sound/Init.bnk > sound/1355168291.bnk)
            dir_name = os.path.dirname(file)
            base_name = os.path.basename(file)
            base_name, _ = os.path.splitext(base_name)
            if base_name.isdigit():
                continue

            hash = fnv.get_hash(base_name)
            idname = f'{hash}.bnk'

            new_file = os.path.join(dir_name, idname)
            if args.recursive:
                if '**' not in new_file:
                    new_file = '**/' + new_file
                glob_files = glob.glob(new_file, recursive=True)
            else:
                glob_files = glob.glob(new_file)

            self._add_files(glob_files, filenames)
            if glob_files:
                logging.info("loading %s from %s", idname, base_name)

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
        parser = wparser.Parser()
        #parser.set_ignore_version(args.ignore_version)
        parser.parse_banks(filenames)
        banks = parser.get_banks(args.bank_repeat)


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
                args.dump_type = wdumper.TYPE_EMPTY
            elif args.txtp or args.viewer:
                # not very useful for txtp/viewer
                args.dump_type = wdumper.TYPE_NONE
            else:
                # default without other flags
                args.dump_type = wdumper.TYPE_XSL_SMALLER
        dumper = wdumper.DumpPrinter(banks, args.dump_type, dump_name)
        dumper.dump()

        # start viewer
        if args.viewer:
            viewer = wview.Viewer(parser)

            logging.info("(stop viewer with CTRL+C)")
            viewer.start(port=args.viewer_port)
            #left open until manually stopped
            viewer.stop()

        txtp_rootdir = os.getcwd()


        # dirs
        locator = wlocator.Locator()
        locator.register_banks(banks)
        locator.set_root_path(txtp_rootdir)
        locator.set_txtp_path(args.txtp_outdir)
        locator.set_wem_path(args.txtp_wemdir)
        locator.setup()

        # !tags.m3u
        tags = wtags.Tags(banks, locator=locator, names=names)
        tags.set_make_event(args.tags_event)
        tags.set_make_wem(args.tags_wem)
        tags.set_add(args.tags_add)
        tags.set_limit(args.tags_limit)

        # generate txtp
        if args.txtp:
            self._generate(args, banks, locator, names, tags)

        # extra
        tags.make()

        if args.file_cleaner:
            cleaner = wcleaner.Cleaner(locator, banks)
            cleaner.process()

        # db manipulation
        if args.dump_type == wdumper.TYPE_NONE and (args.save_lst or args.save_db):
            logging.info("dump set to none, may not save all names")
        if args.save_lst:
            names.save_lst(basename=dump_name)
        if args.save_db:
            names.save_db()
        names.close() #in case DB was open

        if args.tests:
            wtests.Tests().main()

    def _generate(self, args, banks, locator, names, tags):
            # generate txtp
        if not args.txtp:
            return

        #TO-DO multilangs: maybe add some way to exclude making 'sfx' txtp events if lang is selected
        # - hard to know if a sfx bank is used for loading memory web/etc until reading its wem
        # - maybe some filter setting to ignore events from non-localized banks
        # - some localized banks have events with .wem that don't set "localized audio", repeated per localized bank
        #   (ex. MGSurvive stingers)
        langs = [None]
        if args.txtp_lang:
            langs = args.txtp_lang

        for lang in langs:
            generator = wgenerator.Generator(banks, locator, names)
            generator.set_generate_unused(args.txtp_unused)
            generator.set_filter(args.txtp_filter)
            generator.set_filter_rest(args.txtp_filter_rest)
            generator.set_filter_normal(args.txtp_filter_normal)
            generator.set_filter_unused(args.txtp_filter_unused)
            generator.set_gamesyncs(args.txtp_params)
            generator.set_statechunks(args.txtp_statechunks)
            generator.set_statechunks_sd(args.txtp_statechunks_sd)
            generator.set_statechunks_su(args.txtp_statechunks_su)
            generator.set_gamevars(args.txtp_gamevars)
            generator.set_dupes(args.txtp_dupes)
            generator.set_dupes_exact(args.txtp_dupes_exact)
            generator.set_bank_order(args.txtp_bank_order)
            generator.set_renames(args.txtp_renames)

            generator.set_move(args.txtp_move)
            generator.set_name_wems(args.txtp_name_wems)
            generator.set_name_vars(args.txtp_name_vars)
            generator.set_bnkskip(args.txtp_bnkskip)
            generator.set_bnkmark(args.txtp_bnkmark)

            generator.set_alt_exts(args.txtp_alt_exts)
            generator.set_lang(lang)
            generator.set_master_volume(args.txtp_volume)
            generator.set_random_all(args.txtp_random_all)
            generator.set_random_multi(args.txtp_random_multi)
            generator.set_random_force(args.txtp_random_force)
            generator.set_write_delays(args.txtp_write_delays)

            generator.set_tags(tags)

            generator.set_x_noloops(args.txtp_x_noloops)
            generator.set_x_nameid(args.txtp_x_nameid)
            generator.set_x_silence(args.txtp_x_silence)
            generator.set_x_include_fx(args.txtp_x_include_fx)
            generator.set_x_prefilter_paths(args.txtp_x_prefilter_paths)

            generator.generate()
