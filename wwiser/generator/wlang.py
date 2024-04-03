import logging, os


# bank lang info

_LANG_IDS_OLD = 122 #<=

_LANGUAGE_IDS = {
    0x00: "SFX",
    0x01: "Arabic",
    0x02: "Bulgarian",
    0x03: "Chinese(HK)",
    0x04: "Chinese(PRC)",
    0x05: "Chinese(Taiwan)",
    0x06: "Czech",
    0x07: "Danish",
    0x08: "Dutch",
    0x09: "English(Australia)",
    0x0A: "English(India)",
    0x0B: "English(UK)",
    0x0C: "English(US)",
    0x0D: "Finnish",
    0x0E: "French(Canada)",
    0x0F: "French(France)",
    0x10: "German",
    0x11: "Greek",
    0x12: "Hebrew",
    0x13: "Hungarian",
    0x14: "Indonesian",
    0x15: "Italian",
    0x16: "Japanese",
    0x17: "Korean",
    0x18: "Latin",
    0x19: "Norwegian",
    0x1A: "Polish",
    0x1B: "Portuguese(Brazil)",
    0x1C: "Portuguese(Portugal)",
    0x1D: "Romanian",
    0x1E: "Russian",
    0x1F: "Slovenian",
    0x20: "Spanish(Mexico)",
    0x21: "Spanish(Spain)",
    0x22: "Spanish(US)",
    0x23: "Swedish",
    0x24: "Turkish",
    0x25: "Ukrainian",
    0x26: "Vietnamese",
}

_LANGUAGE_HASHNAMES = {
    393239870: "SFX",
    3254137205: "Arabic",
    4238406668: "Bulgarian",
    218471146: "Chinese(HK)",
    3948448560: "Chinese(PRC)",
    2983963595: "Chinese(Taiwan)",
    877555794: "Czech",
    4072223638: "Danish",
    353026313: "Dutch",
    144167294: "English(Australia)",
    1103735775: "English(India)",
    550298558: "English(UK)",
    684519430: "English(US)",
    50748638: "Finnish",
    1024389618: "French(Canada)",
    323458483: "French(France)",
    4290373403: "German",
    4147287991: "Greek",
    919142012: "Hebrew",
    370126848: "Hungarian",
    1076167009: "Indonesian",
    1238911111: "Italian",
    2008704848: "Japanese",
    4224429355: "Japanese(JP)",
    3391026937: "Korean",
    3647200089: "Latin",
    701323259: "Norwegian",
    559547786: "Polish",
    960403217: "Portuguese(Brazil)",
    3928554441: "Portuguese(Portugal)",
    4111048996: "Romanian",
    2577776572: "Russian",
    3484397090: "Slovenian",
    3671217401: "Spanish(Mexico)",
    235381821: "Spanish(Spain)",
    4148950150: "Spanish(US)",
    771234336: "Swedish",
    4036333791: "Turkish",
    4065424201: "Ukrainian",
    2847887552: "Vietnamese",

    # derived just in case, some seen in games
    3383237639: "English",
    3133094709: "French",
    4039628935: "Spanish",
    577468018: "Portuguese",
    1016554174: "Chinese",
}

# common alt names to simplify usage
_LANGUAGE_ALTS = {
    'us': 'en',
    'jp': 'ja',
}

# list also used to sort names in printed info, defaults to most common ones
_LANGUAGE_SHORTNAMES = {
    "SFX": 'sfx',

    "English": 'en',
    "English(US)": 'en', #en-us
    "English(UK)": 'uk', #en-gb
    "Japanese": 'ja',
    "Japanese(JP)": 'ja',

    "Arabic": 'ar',
    "Bulgarian": 'bg',
    "Chinese": 'zh',
    "Chinese(HK)": 'zh-hk',
    "Chinese(PRC)": 'zh-cn',
    "Chinese(Taiwan)": 'zh-tw',
    "Czech": 'cs',
    "Danish": 'da',
    "Dutch": 'nl',
    "English(Australia)": 'en-au',
    "English(India)": 'en-in', #?
    "Finnish": 'fi',
    "French": 'fr',
    "French(Canada)": 'fr-ca',
    "French(France)": 'fr',
    "German": 'de',
    "Greek": 'el',
    "Hebrew": 'he',
    "Hungarian": 'hu',
    "Indonesian": 'id',
    "Italian": 'it',
    "Korean": 'ko',
    "Norwegian": 'no',
    "Polish": 'pl',
    "Portuguese": 'pt',
    "Portuguese(Brazil)": 'pt-br',
    "Portuguese(Portugal)": 'pt',
    "Romanian": 'ro',
    "Russian": 'ru',
    "Slovenian": 'sl',
    "Spanish": 'es',
    "Spanish(Mexico)": 'es-mx',
    "Spanish(Spain)": 'es',
    "Spanish(US)": 'es-us',
    "Swedish": 'sv',
    "Turkish": 'tr',
    "Ukrainian": 'uk',
    "Vietnamese": 'vi',

    "Latin": 'la', #what (used in SM:WoS for placeholder voices, that are reversed audio of misc voices)
}

_LANGUAGES_ORDER = list(_LANGUAGE_SHORTNAMES.keys())

class Lang(object):
    def __init__(self, node):
        self._node = node

        self.shortname = None
        self.fullname = None
        self._load()


    def _load(self):
        nroot = self._node.get_root()
        nlangid = nroot.find1(name='BankHeader').find1(name='dwLanguageID')
        version = nroot.get_version()

        lang_value = nlangid.value()
        if version <= _LANG_IDS_OLD: #set of values
            lang_name = _LANGUAGE_IDS.get(lang_value)
        else: #set of hashed names
            # typical values but languages can be anything (redefined in project options)
            lang_name = _LANGUAGE_HASHNAMES.get(lang_value)
            if not lang_name: #try loaded names (ex. Xenoblade DE uses "en" and "jp")
                lang_name = nlangid.get_attr('hashname')

        if not lang_name:
            lang_name = "%s" % (lang_value)

        lang_short = _LANGUAGE_SHORTNAMES.get(lang_name, lang_name)
        #if lang_short == 'sfx':
        #    lang_short = ''
        self.shortname = lang_short

        #if lang_name == 'SFX':
        #    lang_name = ''
        self.fullname = lang_name

    # checks if current bank's lang matches expected bank (ex. "en" only matches if current bnk is the English(US) lang)
    # SFX/default languages always match (always allowed)
    def matches(self, lang):
        if not lang:
            return True
        if not self.fullname or self.fullname.lower() == 'sfx': #sfx
            return True
        # can pass allowed lang "sfx", meaning any localized banks are ignored
        lang = lang.lower()
        #if lang == 'sfx':
        #    lang = ''
        if lang in _LANGUAGE_ALTS: #simplify...
            lang = _LANGUAGE_ALTS[lang]

        # allow full name "English(US)" or "en"
        return self.fullname.lower() == lang or self.shortname.lower() == lang


def _sorter(elem):
    try:
        fullname = elem[0]
        return _LANGUAGES_ORDER.index(fullname)
    except:
        return 999

# makes a lang list
class Langs(object):
    def __init__(self, banks, localized_only=False):
        self.items = []
        self._localized_only = localized_only
        self._load(banks)

    def _load(self, banks):
        items = []
        for bank in banks:
            lang = Lang(bank)

            # todo improve
            if self._localized_only and lang.fullname == 'SFX':
                continue

            key = (lang.fullname, lang.shortname)
            if key not in items:
                items.append(key)

        items.sort(key=_sorter)
        self.items = items
