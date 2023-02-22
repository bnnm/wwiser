import logging


def setup_clean_logging():
    # removes old handlers in case we call one setup after other setups
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

#to-do: handlers is python3.3+?
def setup_cli_logging():
    setup_clean_logging()
    #handlers = [logging.StreamHandler(sys.stdout)]
    logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            #format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
            #handlers=handlers
    )

def setup_gui_logging(txt):
    setup_clean_logging()
    handlers = [_GuiLogHandler(txt)]
    logging.basicConfig(
            level=logging.INFO,
            format='%(message)s',
            #format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
            handlers=handlers
    )

def setup_file_logging():
    setup_clean_logging()
    #handlers = [logging.FileHandler('wwiser.log')]
    logging.basicConfig(
            #allow DEBUG for extra info
            level=logging.DEBUG,
            format='%(message)s',
            #format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s',
            filename='wwiser.log'
    )

class _GuiLogHandler(logging.Handler):
    def __init__(self, txt):
        logging.Handler.__init__(self)
        self._txt = txt

    def emit(self, message):
        msg = self.format(message)
        txt = self._txt
        txt.config(state='normal')
        txt.insert('end', msg + '\n')
        txt.see('end')
        txt.config(state='disabled')
