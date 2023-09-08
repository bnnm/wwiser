import re
from . import wcleaner_unwanted, wcleaner_unused


class Cleaner(object):
    def __init__(self, locator, banks):
        self._locator = locator
        self._banks = banks

    def process(self):
        cleaner = wcleaner_unused.CleanerUnused(self._locator, self._banks)
        cleaner.process()

        cleaner = wcleaner_unwanted.CleanerUnwanted(self._locator)
        cleaner.process()
