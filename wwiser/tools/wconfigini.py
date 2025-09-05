import logging
import configparser

_CONFIG_NAME = 'wwiser.ini'
_DEFAULT_SECTION = 'wwiser'

class ConfigIni(object):
    def __init__(self):
        self._config = configparser.ConfigParser()

        # ignored if file doesn't exist
        self._config.read('wwiser.ini')

        # inis need to put vars in sections
        try:
            self._config.add_section(_DEFAULT_SECTION)
        except:
            pass #already exists

    def get(self, key):
        try:
            # also: .getboolean, .getint, .getfloat
            return self._config.get(_DEFAULT_SECTION, key)
        except:
            return None #doesn't exists

    def set(self, key, val):
        self._config.set(_DEFAULT_SECTION, key, val)

    def update(self):
        try:
            with open(_CONFIG_NAME, 'w') as f:
                self._config.write(f)
        except PermissionError:
            logging.info("config: can't save .ini (read only dir?)")
            return # may happen in read-only dirs
