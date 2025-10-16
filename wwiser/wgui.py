import os, logging, threading, platform
import tkinter as tk
from tkinter import ttk, font, filedialog, scrolledtext, messagebox
#import zlib,base64

from . import wversion, wlogs
from .names import wnames
from .tools import wcleaner, wconfigini
from .parser import wparser
from .viewer import wdumper, wview
from .generator import wgenerator, wtags, wlocator, wlang


class GuiStyle(ttk.Style):
    def __init__(self, master):
        super(GuiStyle, self).__init__(master)

        master.geometry('980x800')

        # this loads a .tcl theme, easier to handle, but hard to get out from .pyz
        #root.tk.call("source", "theme.tcl")
        #root.tk.call("set_theme", "light")

        # packing values, for external use
        self.pads_frame_top = {'padx':0, 'pady':0, 'ipadx':0, 'ipady':0}
        self.pads_frame = {'padx':10, 'pady':0, 'ipadx':15, 'ipady':15}
        self.pads_frame_min = {'padx':10, 'pady':0, 'ipadx':5, 'ipady':5}
        self.pads_frame_bottom = {'padx':10, 'pady':(0, 10), 'ipadx':10, 'ipady':10}
        self.pads_frame_buttons = {'padx':0, 'pady':0, 'ipadx':0, 'ipady':0}
        self.pads_button = {'padx':(0, 8), 'pady':5, 'ipadx':1, 'ipady':1}
        self.pads_options_grid = {'padx':10, 'pady':5, 'ipadx':1, 'ipady':1}
        self.pads_panel_scrollbar = {'padx':(5,0)}
        self.pads_labeltext = {'padx':0, 'pady':(0, 5), 'ipadx':5, 'ipady':5}
        self.pads_log = {'padx':0, 'pady':(0, 10), 'ipadx':0, 'ipady':0}

        # overwrite system default (windows/linux/max style) with a simple one
        # some widgets like TButton aren't configurable otherwise
        self.theme_use('default') #others: alt, winnative, clam, classic, default, vista, xpnative

        font_main = self._get_font(('Segoe UI','Helvetica','Arial'))
        top_font = self._get_font(('Fixedsys', 'Consolas', 'Monospace', 'Fixedsys'))

        color_back = '#2f3136'
        color_text = '#F0F0F0'
        color_high = '#f1c40f'
        color_bt_b = '#F4F4F4'
        color_bt_f = '#333333'
        color_bm_b = '#00A2DD'
        color_bm_f = '#F0F0F0'
        color_lbl_info = '#999999'
        color_list = '#40444b'

        #TODO: see official defs in https://docs.python.org/3/library/tkinter.ttk.html
        # ttk styles, passed as **kw, so same as configure(val_key:val_val)
        styles = {
            #others: TPanedwindow TRadiobutton TScrollbar TSeparator
            '.': {
                'font': (font_main, 11),
            },
            'TFrame': {
                'background': color_back,
            },
            'Buttons.TFrame': {
            },
            'TLabelframe': {
                'background': color_back, 'padding':(5,2)
            },
            'TLabelframe.Label': {
                'background': color_back, 'foreground': color_text,
            },
            'TButton': {
                'background': color_bt_b, 'foreground': color_bt_f, 'padding': 3, 'highlightthickness':0, 'borderwidth':0,
            },
            'Main.TButton': {
                'background': color_bm_b, 'foreground': color_bm_f,
            },
            'Min.TButton': {
                'padding': 0, 'font': (font_main, 10),
            },
            'TCheckbutton': {
                'background': color_back, 'foreground': color_text, 'font': (font_main, 11), 'padding': (5,1), #'indicatorcolor':'red', 
            },
            'TLabel': {
                'background': color_back, 'foreground': color_text,
            },
            'Top.TLabel': {
                'foreground': color_high, 'font': (top_font, 26), 'weight':'bold', 'underline':0, 
            },
            'Header.TLabel': {
                'foreground': "#00AEEE", 'font': (font_main, 11),
            },
            'Info.TLabel': {
                'foreground': color_lbl_info,  'font': (font_main, 10), 'padding': 3,
            },
            'TEntry': {
                'fieldbackground': '#50545b', 'foreground': color_text, 'padding': 3, 'font': (font_main, 11),
            },
            # not working properly (win/default style issue?)
            'TCombobox': {
                'font': (font_main, 10), 'padding': 3,
                #'foreground': '#50545b',  'fieldbackground': '#50545b', 'selectbackground': '#50545b', 'background': '#50545b',
            },
        }

        for key in styles.keys():
            vals = styles[key]
            if vals:
                self.configure(key, **vals)

        # special props
        self.map('TButton', background=[('active', color_high)], foreground=[('active', color_bt_f)])
        self.map('TCheckbutton', background=[('active', color_back)], indicatorcolor=[('selected', color_high),  ('pressed', color_high)])

        # tk-only styles
        # https://www.tcl.tk/man/tcl8.7/TkCmd/index.html
        master.configure(background=color_back)
        self.theme_canvas = {'background':'white', 'borderwidth':0, 'highlightthickness':0}
        self.theme_scrolledtext = {'background': color_list, 'foreground': color_text, 'borderwidth':0, 'highlightthickness':0}
        self.theme_listbox = {'background': color_list, 'foreground': color_text, 'borderwidth':0, 'highlightthickness':0, 'activestyle': 'none'}


    # different SOs have a bunch of fonts so try first that works
    def _get_font(self, fonts):
        families = font.families()

        for font_test in fonts:
            if font_test in families:
                return font_test
        return 'Default' #ignored probably


# Frames can't have scrollbars, so the only way to make one is to put in other
# component that has them, in this case a canvas with scrollbar, and make a fake window.
# Due to its hackish nature, other components need to be attached to panel.frame.
class ScrollablePanel(ttk.Frame):
    def __init__(self, frame, style, *args, **kwargs):
        super(ScrollablePanel, self).__init__(frame, *args, **kwargs)

        canvas = tk.Canvas(self, **style.theme_canvas)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)

        frame.bind("<Configure>", self._on_configure_frame)
        canvas.bind('<Configure>', self._on_configure_canvas)

        canvas.bind('<Enter>', self._on_enter)
        canvas.bind('<Leave>', self._on_leave)
        scrollbar.bind('<Enter>', self._on_enter)
        scrollbar.bind('<Leave>', self._on_leave)

        window = canvas.create_window((0, 0), window=frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, **style.pads_panel_scrollbar)
        #frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True) #doesn't scroll, see on_configure_canvas

        self.canvas = canvas
        self.frame = frame
        self.window = window

    def _on_configure_frame(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_configure_canvas(self, event):
        # expand frame to canvas
        if self.frame.winfo_reqwidth() != self.canvas.winfo_width():
            self.canvas.itemconfigure(self.window, width=self.canvas.winfo_width())

    def _on_enter(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_leave(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        factor = 120 #on mac this should be 1?

        pos = -1 * (event.delta // factor)
        self.canvas.yview_scroll(pos, "units")



class Gui(object):
    DEFAULT_PORT = wview.DEFAULT_PORT

    def __init__(self):
        # gui state/internals
        self._root_path = None
        self._baseinfo = None

        self._fields = {}
        self._setup_window()

        # bank state/internals
        wlogs.setup_gui_logging(self.txt_log)

        self.parser = wparser.Parser()
        self.viewer = wview.Viewer(self.parser)
        self.names = wnames.Names()
        self.parser.set_names(self.names)

        self.cfg = wconfigini.ConfigIni()

        self._thread_banks = None
        self._thread_dump = None
        self._thread_wwnames = None
        self._thread_txtp = None

        title = 'wwiser'
        if wversion.WWISER_VERSION:
            title += " " + wversion.WWISER_VERSION
        logging.info("%s (python %s)", title, platform.python_version())

        self._update_baseinfo()

    #--------------------------------------------------------------------------

    def _setup_window(self):

        root = tk.Tk()
        #root.resizable(width=False,height=False)

        #icon = zlib.decompress(base64.b64decode('eJxjYGAEQgEBBiDJwZDBy''sAgxsDAoAHEQCEGBQaIOAg4sDIgACMUj4JRMApGwQgF/ykEAFXxQRc='))
        #root.iconbitmap(wloader.Loader.get_resource('resources/wwiser.ico'))
        #root.iconbitmap(icon)

        title = "wwiser"
        if wversion.WWISER_VERSION:
            title += " " + wversion.WWISER_VERSION
        root.title(title)

        # state
        self.root = root

        self.style = GuiStyle(root) #custom ttk.Style(root)

        self._setup_top()
        self._setup_banks()
        self._setup_options()
        self._setup_log()


    def _setup_top(self):
        tframe = ttk.Frame(self.root)
        tframe.pack(side=tk.TOP, fill=tk.BOTH, expand=False, **self.style.pads_frame_top)

        self._top(tframe, "wwiser").pack(side=tk.TOP, anchor=tk.N)


    def _setup_banks(self):
        frame = ttk.Frame(self.root)
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=False, **self.style.pads_frame)

        # header
        sframe = ttk.Frame(frame)
        sframe.pack(side=tk.TOP, fill=tk.BOTH, expand=False)

        self._hdr(sframe, "BANKS").pack(side=tk.LEFT, anchor=tk.NW)
        lbl = self._lbl(sframe, '', info=True)
        lbl.pack(side=tk.RIGHT, anchor=tk.NW)
        self._baseinfo = lbl

        # bank list
        lst = tk.Listbox(frame, selectmode=tk.EXTENDED, height=1, **self.style.theme_listbox)
        scr = ttk.Scrollbar(lst, orient=tk.VERTICAL)
        scr.config(command=lst.yview)
        lst.config(yscrollcommand=scr.set) #TODO: scrollbar refresh causes visible issues

        lst.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        scr.pack(side=tk.RIGHT, fill=tk.Y)

        self.list_box = lst

        # button groups
        gframe = ttk.Frame(frame)
        gframe.pack(side=tk.TOP, fill=tk.BOTH)

        bframe = ttk.Frame(gframe, style='Buttons.TFrame')
        bframe.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._btn(bframe, "Load dirs...", self._load_banks_dir, main=True).pack(side=tk.LEFT, **self.style.pads_button)
        self._btn(bframe, "Load banks...", self._load_banks_files).pack(side=tk.LEFT, **self.style.pads_button)
        #self._chk('bnk_isdir', frame, "Load dir").pack(side=LEFT)
        self._load_dir = False

        bframe = ttk.Frame(gframe, style='Buttons.TFrame')
        bframe.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._btn(bframe, "Generate TXTP", self._generate_txtp, main=True).pack(side=tk.LEFT, **self.style.pads_button)
        self._btn(bframe, "View banks", self._start_viewer).pack(side=tk.LEFT, **self.style.pads_button)
        self._btn(bframe, "Dump banks", self._dump_banks).pack(side=tk.LEFT, **self.style.pads_button)
        #self._btn(bframe, "Stop", self._stop_viewer).pack(side=LEFT, **self.style.pads_button)
        #box = self._box('viewer_port', frame, "Port:", None, width=6)
        #box[0].pack(side=LEFT)
        #box[1].pack(side=LEFT)

        bframe = ttk.Frame(gframe, style='Buttons.TFrame')
        bframe.pack(side=tk.LEFT, fill=tk.X, expand=True)
        #self._chk('ignore_version', bframe, "Ignore version check").pack(side=tk.RIGHT)
        self._btn(bframe, "Unload banks", self._unload_banks, min=True).pack(side=tk.RIGHT, **self.style.pads_button)

    def _setup_options(self):
        #self._sep(root).pack(side=tk.TOP, fill=X, pady=10)

        #frame = ttk.Frame(self.root)
        #frame.pack(side=tk.TOP, fill=tk.BOTH, **self.style.pads_frame_min)

        frame = ttk.Frame(self.root)
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, **self.style.pads_frame)

        self._hdr(frame, "TXTP GENERATOR OPTIONS").pack(side=tk.TOP, anchor=tk.NW)

        spanel = ScrollablePanel(frame, self.style)
        spanel.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        #----------------------------------------------------------------------

        cframe = ttk.Frame(spanel.frame)
        cframe.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        frame = ttk.Labelframe(cframe, text='Base')
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, **self.style.pads_labeltext)
        frame.grid_columnconfigure(0, minsize=80) #weight 2 = x2 of others
        row = 0

        cmb = self._cmb('bank_repeat', frame, 'Repeats:', 'How different banks with same ID + language (such as updates) are handled')
        cmb[0].grid(row=row, column=0, sticky=tk.E)
        cmb[1].grid(row=row, column=1, sticky=tk.W)
        cmb[2].grid(row=row, column=2, sticky=tk.W)

        items = self._fields["bank_repeat"]
        items['values'] = [''] + wparser.Parser.MULTIBANK_MODES #self.parser.MULTIBANK_MODES

        row += 1

        cmb = self._cmb('txtp_lang', frame, 'Language:', 'Current language (select when loading multiple localized banks or set to SFX to skip all localized banks)')
        cmb[0].grid(row=row, column=0, sticky=tk.E)
        cmb[1].grid(row=row, column=1, sticky=tk.W)
        cmb[2].grid(row=row, column=2, sticky=tk.W)

        row += 1

        box = self._box('txtp_outdir', frame, "TXTP subdir:", "Subdir where .txtp are generated (relative to 'base folder', set empty to put all txtp without subdirs)", width=20)
        self._fields['txtp_outdir'].set('txtp/')
        box[0].grid(row=row, column=0, sticky=tk.E)
        box[1].grid(row=row, column=1, sticky=tk.W)
        box[2].grid(row=row, column=2, sticky=tk.W)

        row += 1

        box = self._box('txtp_wemdir', frame, "Wem subdir:", "Subdir where .txtp expects .wem (set * for autofind all .wem/bnk, relative to 'base folder')", width=20)
        self._fields['txtp_wemdir'].set('*')
        box[0].grid(row=row, column=0, sticky=tk.E)
        box[1].grid(row=row, column=1, sticky=tk.W)
        box[2].grid(row=row, column=2, sticky=tk.W)

        #chk = self._chk('txtp_move', frame, "Move referenced .wem to subdir")
        #chk.grid(row=row, column=3, sticky=tk.W, columnspan=2)

        row += 1

        box = self._box('txtp_volume', frame, "Volume:", "Master output volume (*=auto, 2.0=200%, 0.5=50%, -6dB=50%, 6dB=200%)", width=10)
        box[0].grid(row=row, column=0, sticky=tk.E)
        box[1].grid(row=row, column=1, sticky=tk.W)
        box[2].grid(row=row, column=2, sticky=tk.W)
        row += 1

        self._fields['txtp_volume'].set('*')


        frame = ttk.Labelframe(cframe, text='State')
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, **self.style.pads_labeltext)
        frame.grid_columnconfigure(0, minsize=80) #weight 2 = x2 of others
        row = 0

        box = self._box('txtp_params', frame, "Params:", "List of '(state=value) [switch=value] ...' to force (default: all)", width=80)
        box[0].grid(row=row, column=0, sticky=tk.E)
        box[1].grid(row=row, column=1, sticky=tk.W)
        box[2].grid(row=row, column=2, sticky=tk.W)
        row += 1

        box = self._box('txtp_statechunks', frame, "Statechunks:", "List of 'state=value ...' to set (for crossfading .txtp)", width=80)
        box[0].grid(row=row, column=0, sticky=tk.E)
        box[1].grid(row=row, column=1, sticky=tk.W)
        box[2].grid(row=row, column=2, sticky=tk.W)
        row += 1

        box = self._box('txtp_gamevars', frame, "Gamevars:", "List of 'name=float-value ...' to set (for crossfading .txtp)", width=80)
        box[0].grid(row=row, column=0, sticky=tk.E)
        box[1].grid(row=row, column=1, sticky=tk.W)
        box[2].grid(row=row, column=2, sticky=tk.W)
        row += 1

        box = self._box('txtp_renames', frame, "Renames:", "List of 'text-in:text-out ...' parts to rename in .txtp", width=80)
        box[0].grid(row=row, column=0, sticky=tk.E)
        box[1].grid(row=row, column=1, sticky=tk.W)
        box[2].grid(row=row, column=2, sticky=tk.W)
        row += 1

        box = self._box('txtp_filter', frame, "Filter:", "List of allowed events/IDs/bnk/etc (use - to exclude)", width=80)
        box[0].grid(row=row, column=0, sticky=tk.E)
        box[1].grid(row=row, column=1, sticky=tk.W)
        box[2].grid(row=row, column=2, sticky=tk.W)
        row += 1

        frame = ttk.Labelframe(cframe, text="Filters")
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, **self.style.pads_labeltext)
        row = 0

        chk = self._chk('txtp_unused', frame, "Generate unused audio (use when log complains)")
        chk.grid(row=row, column=0, columnspan=3, sticky=tk.W)

        chk = self._chk('txtp_statechunks_sd', frame, "Skip default statechunk")
        chk.grid(row=row, column=3, columnspan=2, sticky=tk.W)

        row += 1

        chk = self._chk('txtp_dupes', frame, "Allow TXTP dupes (WARNING: may create a lot)")
        chk.grid(row=row, column=0, columnspan=3, sticky=tk.W)

        chk = self._chk('txtp_filter_normal', frame, "Skip normal txtp (for testing)")
        chk.grid(row=row, column=3, columnspan=2, sticky=tk.W)

        row += 1

        chk = self._chk('txtp_filter_rest', frame, "Generate rest of files after filtering (prioritizes names)")
        chk.grid(row=row, column=0, columnspan=3, sticky=tk.W)

        chk = self._chk('txtp_filter_unused', frame, "Skip unused txtp (for testing)")
        chk.grid(row=row, column=3, columnspan=2, sticky=tk.W)

        #chk = self._chk('txtp_bank_order', frame, "Generate TXTP in bank order instead of names first (alters which txtp are considered dupes)")
        #chk.grid(row=row, column=0, columnspan=4, sticky=tk.W)

        row += 1

        frame = ttk.Labelframe(cframe, text="Misc")
        frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, **self.style.pads_labeltext)

        chk = self._chk('txtp_random_all', frame, "Groups: make multiple .txtp per base 'random'")
        chk.grid(row=row, column=0, sticky=tk.W)

        chk = self._chk('txtp_x_include_fx', frame, "Apply FX volumes")
        chk.grid(row=row, column=1, sticky=tk.W)

        row += 1

        chk = self._chk('txtp_random_force', frame, "Groups: force base groups to be selectable like 'random'")
        chk.grid(row=row, column=0, sticky=tk.W)

        chk = self._chk('txtp_alt_exts', frame, "Use alt extensions (.logg/lwav)")
        chk.grid(row=row, column=1, sticky=tk.W)

        row += 1

        chk = self._chk('txtp_random_multi', frame, "Groups: force multiloops to be selectable like 'random'")
        chk.grid(row=row, column=0, sticky=tk.W)

        chk = self._chk('tags_event', frame, "Use shorter .txtp names and put full names in !tags.m3u")
        chk.grid(row=row, column=1, sticky=tk.W)

        #frame = ttk.Labelframe(cframe, text="Misc")
        #frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, **self.style.pads_labeltext)
        #row = 0

        #chk = self._chk('txtp_lang', frame, "Mark .txtp and set .wem subdir per language")
        #chk.grid(row=row, column=0, sticky=tk.W)

        #chk = self._chk('txtp_bnkmark', frame, "Mark .txtp that use internal .bnk (reference)")
        #chk.grid(row=row, column=1, sticky=tk.W)

        #chk = self._chk('txtp_name_wems', frame, "Add .wem names to .txtp filename (if found)")
        #chk.grid(row=row, column=2, sticky=tk.W)

        #row += 1

        #chk = self._chk('txtp_bnkskip', frame, "Treat internal (in .bnk) .wem as if external")
        #chk.grid(row=row, column=1, sticky=tk.W)

        #chk = self._chk('txtp_name_vars', frame, "Add ignored variables to .txtp filename")
        #chk.grid(row=row, column=2, sticky=tk.W)

        #row += 1

        #chk = self._chk('txtp_write_delays', frame, "Don't skip initial delay")
        #chk.grid(row=row, column=0, sticky=tk.W)

        #chk = self._chk('txtp_x_silence', frame, "Silence parts that crossfade by default")
        #chk.grid(row=row, column=1, sticky=tk.W)

        #row += 1

        #frame = ttk.Labelframe(cframe, text="Tags")
        #frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, **self.style.pads_labeltext)
        #row = 0

        #chk = self._chk('tags_wem', frame, "Make !tags.m3u for .wem in folder")
        #chk.grid(row=row, column=1, sticky=tk.W)


    #----------------------------------------------------------------------

    def _setup_log(self):
        self._sep(self.root).pack(side=tk.TOP, fill=tk.X, pady=5)

        frame = ttk.Frame(self.root)
        frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, **self.style.pads_frame_bottom) #set true to add extra size

        self._hdr(frame, "LOG").pack(side=tk.TOP, anchor=tk.NW)

        log = scrolledtext.ScrolledText(frame, width=40, height=1, **self.style.theme_scrolledtext)
        log.pack(side=tk.TOP, fill=tk.BOTH, expand=True, **self.style.pads_log)
        log.config(state=tk.DISABLED)
        self.txt_log = log

        self._btn(frame, "Clear Log", self._clear_log, min=True).pack(side=tk.LEFT)
        self._chk('log', frame, "Write wwiser.log (extra info)", self._change_log).pack(side=tk.LEFT, **self.style.pads_button)

        self._btn(frame, "Redump clean wwnames.txt", self._dump_wwnames, min=True).pack(side=tk.LEFT, **self.style.pads_button)
        #self._chk('ww_missing', frame, "Also include missing IDs").pack(side=tk.LEFT)

        self._btn(frame, "Make !tags.m3u for .wem", self._generate_tags, min=True).pack(side=tk.LEFT, **self.style.pads_button)

        self._btn(frame, "Move .wem/bnk not used in .txtp", self._clean_output, min=True).pack(side=tk.LEFT, **self.style.pads_button)

        self._btn(frame, "Exit", self._exit, min=True).pack(side=tk.RIGHT)

        return

    #--------------------------------------------------------------------------
    
    def _update_baseinfo(self):
        info = 'Base folder: '
        path = self._root_path
        if not path:
            path = '-'
        self._baseinfo.configure(text=info + path)

    #--------------------------------------------------------------------------
    # ELEMS

    def _box(self, field, frame, text, info, width=50, type=None):
        lbl = ttk.Label(frame, text=text)
        if   type == 'int':
            var = tk.IntVar()
        elif type == 'float':
            var = tk.DoubleVar()
        else:
            var = tk.StringVar()

        ent = ttk.Entry(frame, textvariable=var, width=width)
        if info:
            inf = ttk.Label(frame, text=info, style='Info.TLabel')
        else:
            inf = None
        self._fields[field] = var
        return (lbl, ent, inf)

    def _top(self, frame, text):
        lbl = ttk.Label(frame, text=text, style="Top.TLabel")
        return lbl

    def _hdr(self, frame, text):
        lbl = ttk.Label(frame, text=text, style='Header.TLabel')
        return lbl

    def _lbl(self, frame, text, info=False):
        lbl = ttk.Label(frame, text=text)
        if info:
            lbl.configure(style='Info.TLabel')
        return lbl

    def _btn(self, frame, text, command, main=False, min=False):
        style = None
        if main:
            style = 'Main.TButton'
        if min:
            style = 'Min.TButton'
        btn = ttk.Button(frame, text=text, command=command, style=style)
        return btn

    def _sep(self, frame):
        sep = ttk.Separator(frame)
        return sep

    def _chk(self, field, frame, text, command=None):
        var = tk.BooleanVar()
        var.set(False)
        chk = ttk.Checkbutton(frame, text=text, variable=var, command=command)
        self._fields[field] = var
        return chk

    def _cmb(self, field, frame, text, info, width=18):
        lbl = ttk.Label(frame, text=text)

        cmb = ttk.Combobox(frame, width=width, state='readonly', values=None, style='TCombobox')

        if info:
            inf = ttk.Label(frame, text=info, style='Info.TLabel')
        else:
            inf = None

        self._fields[field] = cmb
        return (lbl, cmb, inf)

    def start(self):
        self.root.mainloop()

    #--------------------------------------------------------------------------

    def _load_banks_files(self):
        self._load_dir = False
        self._load_banks()

    def _load_banks_dir(self):
        self._load_dir = True
        self._load_banks()

    def _load_banks(self):
        if self._thread_banks and self._thread_banks.is_alive():
            logging.info("gui: parser still working (may be slow, be patient)")
            return
        self._thread_banks = threading.Thread(target = self._load_banks_start)
        self._thread_banks.start()

    def _load_banks_start(self):
        #current_dir = os.path.dirname(os.path.realpath(__file__)) #less useful
        current_dir = os.getcwd()

        last_path = self.cfg.get('last_path')
        if last_path:
            current_dir = last_path

        is_dir = self._load_dir
        if is_dir:
            dirname = filedialog.askdirectory(parent=self.root, initialdir=current_dir)
            if not dirname:
                return
            filenames = []
            for root, _, files in os.walk(dirname):

                for file in files:
                    pathname = os.path.join(root, file)
                    if not file.endswith('.bnk') or not os.path.isfile(pathname):
                        continue
                    filenames.append(pathname)

            #TODO detect depending on all loaded dirs? (may load multiple times)
            current_dir = dirname

        else:
            filenames = filedialog.askopenfilenames(initialdir=current_dir, filetypes = (("Wwise bank files","*.bnk"),("All files","*.*")))
            if filenames:
                current_dir = os.path.dirname(filenames[0])

        # load base dir but only if there wasn't one (IOW uses first dir or first single .bnk)
        prev_banks = self.parser.get_banks()
        if current_dir and not prev_banks:
            self._root_path = current_dir

            # keep last dir around
            self.cfg.set('last_path', self._root_path)
            self.cfg.update()
            self._update_baseinfo()

        if not filenames:
            return

        # dumb normalizer (not needed but for consistency)
        filenames = [ item.replace('\\','/') for item in filenames ]

        #self.parser.set_ignore_version( self._fields['ignore_version'].get() )
        loaded_filenames = self.parser.parse_banks(filenames)
        for file in loaded_filenames:
            if file.startswith(self._root_path):
                file = file[len(self._root_path):]
                if file.startswith('/'):
                    file = file[1:]
            self.list_box.insert(tk.END, file)

        banks = self.parser.get_banks()
        names = self.names
        names.parse_files(banks, loaded_filenames)

        self._update_langs()


    def _unload_banks(self):
        indexes = self.list_box.curselection()
        if not indexes:
            messagebox.showerror('Error', 'Select one or more banks')
            return

        indexes = list(indexes)
        indexes.sort()
        for index in indexes:
            bank = self.list_box.get(index)
            if self._root_path:
                bank = os.path.join(self._root_path, bank)
                bank = bank.replace('\\','/') #dumb normalizer
            self.parser.unload_bank(bank)

        indexes.reverse() #in reverse order b/c indexes disappear
        for index in indexes:
            self.list_box.delete(index)

        self._update_langs()

    #--------------------------------------------------------------------------

    def _get_dump_infoname(self):
        filenames = self.parser.get_filenames()
        if not filenames:
            messagebox.showerror('Error', 'Load one or more banks')
            return None

        #base_path = os.path.dirname(filenames[0])
        base_path = self._root_path
        if len(filenames) == 1:
            base_name = os.path.basename(filenames[0])
        else:
            base_name = 'banks'
        return (base_path, base_name)

    def _dump_call(self, thread, target):
        if thread and thread.is_alive():
            logging.info("gui: dumper still working (may be slow, be patient)")
            return
        thread = threading.Thread(target=target)
        thread.start()

    def _dump_banks(self):
        self._dump_call(self._thread_dump, self._dump_banks_start)

    def _dump_banks_start(self):
        infoname = self._get_dump_infoname()
        if not infoname:
            return
        _, base_name = infoname
        default_name = base_name + '.xml'

        filetypes = (
            ("XML file",".xml"),
            ("XML file (extra small)",".xs.xml"),
            ("XML file (complete)",".c.xml"),
            ("TXT file",".txt")
        )
        outpath = filedialog.asksaveasfilename(initialfile=default_name, defaultextension="*.*", filetypes=filetypes)
        if not outpath:
            return

        dump_type = None
        dump_types = (
            (".xml", wdumper.TYPE_XSL_SMALLER),
            (".xs.xml", wdumper.TYPE_XSL_XS),
            (".c.xml", wdumper.TYPE_XSL),
            (".txt", wdumper.TYPE_TXT),
        )
        
        for ext, type in dump_types:
            if outpath.endswith(ext):
                dump_type = type
        if not dump_type:
            messagebox.showerror('Error', 'Unknown output format')
            return

        dump_name, _ = os.path.splitext(outpath)

        dumper = wdumper.DumpPrinter(self.parser.get_banks(), dump_type, dump_name)
        dumper.dump()

    def _dump_wwnames(self):
        self._dump_call(self._thread_wwnames, self._dump_wwnames_start)

    def _dump_wwnames_start(self):
        infoname = self._get_dump_infoname()
        if not infoname:
            return
        base_path, base_name = infoname
        dump_name = base_name
        dump_type = wdumper.TYPE_EMPTY

        # force read everything first with a special type (to get every possible name)
        dumper = wdumper.DumpPrinter(self.parser.get_banks(), dump_type, dump_name)
        dumper.dump()

        # save new wwnames.txt
        self.names.save_lst(basename=dump_name, path=base_path)

    #--------------------------------------------------------------------------

    def _start_viewer(self):
        # viewer can work without nothing loaded but probably it's easier to understand
        banks = self.parser.get_banks()
        if not banks:
            messagebox.showerror('Error', 'Load one or more banks')
            return

        port = None
        #try:
        #    port = int(self._fields['viewer_port'].get())
        #except ValueError:
        #    port = None

        try:
            self.viewer.start(port, blocking=False)
        except:
            messagebox.showerror('Error', 'Could not start viewer')

    def _stop_viewer(self):
        if not self.viewer:
            messagebox.showerror('Error', 'Viewer not started')
            return
        self.viewer.stop()

    #--------------------------------------------------------------------------

    def _update_langs(self):
        banks = self.parser.get_banks()
        langs = wlang.Langs(banks)

        # convert items 
        items = []
        for fullname, shortname in langs.items:
            items.append(fullname)

        cmb = self._fields["txtp_lang"]
        cmb['values'] = [''] + items


    def _generate_txtp(self):
        self._run(self._generate_txtp_start)

    def _generate_txtp_start(self):
        self._process(make_txtp=True)

    def _generate_tags(self):
        self._run(self._generate_tags_start)

    def _generate_tags_start(self):
        self._process(make_tags=True)

    def _clean_output(self):
        self._run(self._clean_output_start)

    def _clean_output_start(self):
        self._process(make_clean=True)

    def _run(self, target):
        if self._thread_txtp and self._thread_txtp.is_alive():
            logging.info("gui: generator still working (may be slow, be patient)")
            return
        self._thread_txtp = threading.Thread(target = target)
        self._thread_txtp.start()

    def _get_list(self, name):
        items = None
        if self._fields[name].get() != '':
            items = self._fields[name].get().split()
        return items

    def _get_item(self, name):
        return self._fields[name].get()

    def _process(self, **args):
        try:
            self._process_main(**args)
        except Exception as e:
            logging.error("gui: process stopped on error")
            logging.error(e)
            #raise

    def _process_main(self, make_txtp=False, make_tags=False, make_clean=False):
        repeat_mode = self._get_list('bank_repeat')
        if repeat_mode: #TODO: better way to handle
            repeat_mode = repeat_mode[0]

        banks = self.parser.get_banks(repeat_mode)
        if not banks:
            messagebox.showerror('Error', 'Load one or more banks')
            return

        # dirs
        locator = wlocator.Locator()
        locator.register_banks(banks)
        locator.set_root_path( self._root_path )
        locator.set_txtp_path( self._get_item('txtp_outdir') )
        locator.set_wem_path( self._get_item('txtp_wemdir') )
        locator.setup()

        # !tags.m3u
        tags = wtags.Tags(banks, locator=locator, names=self.names)
        tags.set_make_event( self._get_item('tags_event') )
        tags.set_make_wem( make_tags )
        #tags.set_make_wem( self._get_item('tags_wem') )
        #tags.set_add(args.tags_add)
        #tags.set_limit(args.tags_limit)

        if make_txtp:
            generator = wgenerator.Generator(banks, locator, self.names)
            generator.set_filter( self._get_list('txtp_filter') )
            generator.set_filter_rest( self._get_item('txtp_filter_rest') )
            generator.set_filter_normal( self._get_item('txtp_filter_normal') )
            generator.set_filter_unused( self._get_item('txtp_filter_unused') )
            generator.set_gamesyncs( self._get_list('txtp_params') )
            generator.set_statechunks( self._get_list('txtp_statechunks') )
            generator.set_gamevars( self._get_list('txtp_gamevars') )
            #generator.set_bank_order( self._get_item('txtp_bank_order') )
            generator.set_renames( self._get_list('txtp_renames') )

            generator.set_statechunks_sd( self._get_item('txtp_statechunks_sd') )

            generator.set_master_volume( self._get_item('txtp_volume') )
            generator.set_lang( self._get_item('txtp_lang') )
            #generator.set_move( self._get_item('txtp_move') )
            #generator.set_bnkskip( self._get_item('txtp_bnkskip') )
            #generator.set_bnkmark( self._get_item('txtp_bnkmark') )
            #generator.set_name_wems( self._get_item('txtp_name_wems') )
            #generator.set_name_vars( self._get_item('txtp_name_vars') )
            generator.set_generate_unused( self._get_item('txtp_unused') )
            generator.set_alt_exts( self._get_item('txtp_alt_exts') )
            generator.set_dupes( self._get_item('txtp_dupes') )
            generator.set_random_all( self._get_item('txtp_random_all') )
            generator.set_random_multi( self._get_item('txtp_random_multi') )
            generator.set_random_force( self._get_item('txtp_random_force') )
            #generator.set_write_delays( self._get_item('txtp_write_delays') )
            #generator.set_x_silence( self._get_item('txtp_x_silence') )
            generator.set_x_include_fx( self._get_item('txtp_x_include_fx') )

            generator.set_tags(tags)

            generator.generate()

        # extra
        tags.make()

        if make_clean:
            cleaner = wcleaner.Cleaner(locator, banks)
            cleaner.process()

    #--------------------------------------------------------------------------

    def _clear_log(self):
        self.txt_log.config(state=tk.NORMAL)
        self.txt_log.delete(1.0, tk.END)
        self.txt_log.config(state=tk.DISABLED)

    def _change_log(self):
        if  self._get_item('log'):
            wlogs.setup_file_logging()
        else:
            wlogs.setup_gui_logging(self.txt_log)

    def _exit(self):
        if self.names:
            self.names.close()
        if self.viewer:
            self.viewer.stop()

        self.root.destroy()
