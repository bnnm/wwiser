import os, logging, threading, platform
from tkinter import *
from tkinter import ttk, font, filedialog, scrolledtext, messagebox
from . import wnames, wparser, wprinter, wview, wutil, wgenerator, wversion


class Gui(object):
    DEFAULT_PORT = wview.DEFAULT_PORT

    def __init__(self):
        # gui state/internals
        self._fields = {}
        self._setup_window()

        # bank state/internals
        wutil.setup_gui_logging(self.txt_log)

        self.parser = wparser.Parser()
        self.viewer = wview.Viewer(self.parser)
        self.names = wnames.Names()
        self.parser.set_names(self.names)

        self._thread_banks = None
        self._thread_dump = None
        self._thread_txtp = None

        title = 'wwiser'
        if wversion.WWISER_VERSION:
            title += " " + wversion.WWISER_VERSION
        logging.info("%s (python %s)", title, platform.python_version())

    #--------------------------------------------------------------------------

    def _setup_window(self):

        #----------------------------------------------------------------------
        # base

        root = Tk()
        root.geometry('700x800')
        #root.resizable(width=False,height=False)
        #root.iconbitmap(wutil.Loader.get_resource('/resources/wwiser.ico'))

        title = "WWISER"
        if wversion.WWISER_VERSION:
            title += " " + wversion.WWISER_VERSION
        root.title(title)

        self._top(root, "WWISER GUI").pack(side=TOP)

        # state
        self.root = root

        #----------------------------------------------------------------------
        # banks

        frame = ttk.Frame(root)
        frame.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)

        self._lbl(frame, "Banks:").pack(side=TOP, fill=BOTH)

        lst = Listbox(frame, selectmode=EXTENDED, height=20)
        scr = Scrollbar(lst, orient="vertical")
        scr.config(command=lst.yview)
        lst.config(yscrollcommand=scr.set)

        lst.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)
        scr.pack(side=RIGHT, fill=Y)
        self.list_box = lst

        self._btn(frame, "Load...", self._load_banks).pack(side=LEFT)
        self._chk('bnk_isdir', frame, "Load dir").pack(side=LEFT)
        self._btn(frame, "Unload", self._unload_banks).pack(side=LEFT)
        self._btn(frame, "Dump", self._dump_banks).pack(side=LEFT)
        self._chk('ignore_version', frame, "Ignore version check").pack(side=RIGHT)

        #----------------------------------------------------------------------
        # viewer

        self._sep(root).pack(side=TOP, fill=X, pady=10)

        frame = ttk.Frame(root)
        frame.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)

        self._lbl(frame, "Viewer (web browser tool):").pack(side=LEFT)

        self._btn(frame, "Start", self._start_viewer).pack(side=LEFT)
        self._btn(frame, "Stop", self._stop_viewer).pack(side=LEFT)

        box = self._box('viewer_port', frame, "Port:", None, width=6)
        box[0].pack(side=LEFT)
        box[1].pack(side=LEFT)

        #----------------------------------------------------------------------
        # txtp

        self._sep(root).pack(side=TOP, fill=X, pady=10)

        frame = ttk.Frame(root)
        frame.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)
        frame.grid_columnconfigure(2, minsize=50)

        lbl = self._lbl(frame, "TXTP generator:")
        lbl.grid(row=0, column=0)

        btn = self._btn(frame, "Generate", self._generate_txtp)
        btn.grid(row=0, column=1)

        box = self._box('txtp_wemdir', frame, "Wem dir:", "Dir where .txtp expects .wem", width=20)
        self._fields['txtp_wemdir'].set('wem/')
        box[0].grid(row=0, column=3, sticky="E")
        box[1].grid(row=0, column=4, sticky="WE")
        box[2].grid(row=0, column=5, sticky="W")


        frame = ttk.Frame(root)
        frame.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)

        box = self._box('txtp_filter', frame, "Filter:", "List of allowed HIRCs ID/name/classnames", width=50)
        box[0].grid(row=0, column=0, sticky="E")
        box[1].grid(row=0, column=1, sticky="W")
        box[2].grid(row=0, column=2, sticky="W")

        box = self._box('txtp_params', frame, "Params:", "List of '(state=value) [switch=value] ...'", width=50)
        box[0].grid(row=1, column=0, sticky="E")
        box[1].grid(row=1, column=1, sticky="W")
        box[2].grid(row=1, column=2, sticky="W")

        frame = ttk.Frame(root)
        frame.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)

        box = self._box('txtp_volume', frame, "Volume:", "Set master TXTP volume (2.0=200%, 0.5=50%, -6dB=50%, 6dB=200%)", width=10)
        box[0].grid(row=2, column=0, sticky="E")
        box[1].grid(row=2, column=1, sticky="W")
        box[2].grid(row=2, column=2, sticky="W")


        frame = ttk.Frame(root)
        frame.pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)

        chk = self._chk('txtp_move', frame, "Move .wem referenced in banks to wem subdir")
        chk.grid(row=0, column=0, sticky="W")

        chk = self._chk('txtp_lang', frame, "Mark .txtp and set .wem subdir per language")
        chk.grid(row=0, column=1, sticky="W")

        chk = self._chk('txtp_bnkskip', frame, "Treat internal (in .bnk) .wem as if external")
        chk.grid(row=1, column=0, sticky="W")

        chk = self._chk('txtp_bnkmark', frame, "Mark .txtp that use internal .bnk (for reference)")
        chk.grid(row=1, column=1, sticky="W")

        chk = self._chk('txtp_wemname', frame, "Add all .wem names to .txtp filename (if found)")
        chk.grid(row=2, column=0, sticky="W")

        chk = self._chk('txtp_unused', frame, "Generate unused audio (when log complains, load more banks first)")
        chk.grid(row=2, column=1, sticky="W")

        chk = self._chk('txtp_alt_exts', frame, "Use TXTP alt extensions (.logg/lwav)")
        chk.grid(row=3, column=0, sticky="W")

        chk = self._chk('txtp_dupes', frame, "Allow TXTP dupes (WARNING: may create a lot)")
        chk.grid(row=3, column=1, sticky="W")

        chk = self._chk('txtp_random_all', frame, "Make multiple .txtp per base 'random' section")
        chk.grid(row=4, column=0, sticky="W")

        chk = self._chk('txtp_random_force', frame, "Force base section to be selectable like a 'random' section")
        chk.grid(row=4, column=1, sticky="W")

        chk = self._chk('txtp_tagsm3u', frame, "Use shorter .txtp names and put full names in !tags.m3u")
        chk.grid(row=5, column=0, sticky="W")

        #----------------------------------------------------------------------
        # log

        self._sep(root).pack(side=TOP, fill=X, pady=10)

        frame = ttk.Frame(root)
        frame.pack(side=BOTTOM, fill=BOTH, expand=True, padx=5, pady=5)

        log = self._log(frame, "Log:")
        log[0].pack(side=TOP, fill=BOTH)
        log[1].pack(side=TOP, fill=BOTH, expand=True, padx=5, pady=5)
        self.txt_log = log[1]

        self._btn(frame, "Clear Log", self._clear_log).pack(side=LEFT)
        self._chk('log', frame, "Write info to wwiser log (has extra messages)", self._change_log).pack(side=LEFT)
        self._btn(frame, "Exit", self._exit).pack(side=RIGHT)

        return

    #--------------------------------------------------------------------------

    def _box(self, field, frame, text, info, width=50, type=None):
        lbl = ttk.Label(frame, text=text)
        if   type == 'int':
            var = IntVar()
        elif type == 'float':
            var = DoubleVar()
        else:
            var = StringVar()

        ent = ttk.Entry(frame, textvariable=var, width=width)
        if info:
            inf = ttk.Label(frame, text=info)
        else:
            inf = None
        self._fields[field] = var
        return (lbl, ent, inf)

    def _top(self, frame, text):
        fnt = font.Font(size=16, weight='bold', underline=0)
        lbl = ttk.Label(frame, text=text, font=fnt)
        return lbl

    def _btn(self, frame, text, command):
        btn = ttk.Button(frame, text=text, command=command)
        return btn

    def _log(self, frame, text):
        lbl = ttk.Label(frame, text=text)
        txt = scrolledtext.ScrolledText(frame, width=40, height=10)
        txt.config(state=DISABLED)
        return lbl, txt

    def _lbl(self, frame, text):
        lbl = ttk.Label(frame, text=text)
        return lbl

    def _sep(self, frame):
        sep = ttk.Separator(frame)
        return sep

    def _chk(self, field, frame, text, command=None):
        var = BooleanVar()
        var.set(False)
        chk = ttk.Checkbutton(frame, text=text, variable=var, command=command)
        self._fields[field] = var
        return chk


    def start(self):
        self.root.mainloop()

    #--------------------------------------------------------------------------

    def _load_banks(self):
        if self._thread_banks and self._thread_banks.is_alive():
            logging.info("gui: parser still working (may be slow, be patient)")
            return
        self._thread_banks = threading.Thread(target = self._load_banks_start)
        self._thread_banks.start()

    def _load_banks_start(self):
        #current_dir = os.path.dirname(os.path.realpath(__file__)) #less useful
        current_dir = os.getcwd()

        is_dir = self._fields['bnk_isdir'].get()
        if is_dir:
            dirname = filedialog.askdirectory(parent=self.root, initialdir=current_dir)
            if not dirname:
                return
            filenames = []
            for filename in os.listdir(dirname):
                pathname = os.path.join(dirname, filename)
                if not filename.endswith('.bnk') or not os.path.isfile(pathname):
                    continue
                filenames.append(pathname)
        else:
            filenames = filedialog.askopenfilenames(filetypes = (("Wwise bank files","*.bnk"),("All files","*.*")))

        if not filenames:
            return

        self.parser.set_ignore_version( self._fields['ignore_version'].get() )
        loaded_filenames = self.parser.parse_banks(filenames)
        for filename in loaded_filenames:
            self.list_box.insert(END, filename)

        banks = self.parser.get_banks()
        names = self.names
        names.parse_files(banks, loaded_filenames)


    def _unload_banks(self):
        indexes = self.list_box.curselection()
        if not indexes:
            messagebox.showerror('Error', 'Select one or more banks')
            return

        for index in indexes:
            bank = self.list_box.get(index)
            self.parser.unload_bank(bank)
            self.list_box.delete(index)

    #--------------------------------------------------------------------------

    def _dump_banks(self):
        if self._thread_dump and self._thread_dump.is_alive():
            logging.info("gui: dumper still working (may be slow, be patient)")
            return
        self._thread_dump = threading.Thread(target = self._dump_banks_start)
        self._thread_dump.start()

    def _dump_banks_start(self):
        filenames = self.parser.get_filenames()
        if not filenames:
            messagebox.showerror('Error', 'Load one or more banks')
            return

        if len(filenames) == 1:
            default_name = os.path.basename(filenames[0]) + '.xml'
        else:
            default_name = 'banks.xml'

        outpath = filedialog.asksaveasfilename(initialfile=default_name, filetypes = (("XML file","*.xml"),("TXT file","*.txt")))
        if not outpath:
            return

        dump_name, dump_type = os.path.splitext(outpath)
        dump_type = dump_type.lower()[1:]
        if dump_type not in ['xml', 'txt']:
            messagebox.showerror('Error', 'Unknown output format')
            return
        if dump_type == 'xml':
            dump_type = 'xsl'

        printer = wprinter.Printer(self.parser.get_banks(), dump_type, dump_name)
        printer.dump()

    #--------------------------------------------------------------------------

    def _start_viewer(self):
        try:
            port = int(self._fields['viewer_port'].get())
        except ValueError:
            port = None

        try:
            self.viewer.start(port, blocking=False)
        except:
            messagebox.showerror('Error', 'Could not start viewer')
            #todo log

    def _stop_viewer(self):
        if not self.viewer:
            messagebox.showerror('Error', 'Viewer not started')
            return
        self.viewer.stop()

    #--------------------------------------------------------------------------

    def _generate_txtp(self):
        if self._thread_txtp and self._thread_txtp.is_alive():
            logging.info("gui: generator still working (may be slow, be patient)")
            return
        self._thread_txtp = threading.Thread(target = self._generate_txtp_start)
        self._thread_txtp.start()

    def _generate_txtp_start(self):
        banks = self.parser.get_banks()
        if not banks:
            messagebox.showerror('Error', 'Load one or more banks')
            return

        try:
            filter = None
            params = None
            if self._fields['txtp_filter'].get() != '':
                filter = self._fields['txtp_filter'].get().split()
            if self._fields['txtp_params'].get() != '':
                params = self._fields['txtp_params'].get().split()

            generator = wgenerator.Generator(banks)
            generator.set_filter(filter)
            generator.set_params(params)
            #generator.set_outdir(self.fields['txtp_outdir'].get())
            generator.set_wemdir(self._fields['txtp_wemdir'].get())
            generator.set_volume(self._fields['txtp_volume'].get())
            generator.set_lang(self._fields['txtp_lang'].get())
            generator.set_move(self._fields['txtp_move'].get())
            generator.set_bnkskip(self._fields['txtp_bnkskip'].get())
            generator.set_bnkmark(self._fields['txtp_bnkmark'].get())
            generator.set_wemnames(self._fields['txtp_wemname'].get())
            generator.set_generate_unused(self._fields['txtp_unused'].get())
            generator.set_alt_exts(self._fields['txtp_alt_exts'].get())
            generator.set_dupes(self._fields['txtp_dupes'].get())
            generator.set_random_all(self._fields['txtp_random_all'].get())
            generator.set_random_force(self._fields['txtp_random_force'].get())
            generator.set_random_force(self._fields['txtp_tagsm3u'].get())

            generator.generate()

        except Exception:
            logging.error("gui: generator stopped on error")
            #raise

    #--------------------------------------------------------------------------

    def _clear_log(self):
        self.txt_log.config(state=NORMAL)
        self.txt_log.delete(1.0, END)
        self.txt_log.config(state=DISABLED)
        #self.txt_log_main.config(state=NORMAL)
        #self.txt_log_main.delete(1.0, END)
        #self.txt_log_main.config(state=DISABLED)

    def _change_log(self):
        if self._fields['log'].get():
            wutil.setup_file_logging()
        else:
            wutil.setup_gui_logging(self.txt_log)

    def _exit(self):
        if self.names:
            self.names.close()
        if self.viewer:
            self.viewer.stop()

        self.root.destroy()
