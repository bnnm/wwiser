import logging, re, os, os.path, sys


class Config(object):

    def __init__(self):
        #self._names = names

        self.disable_fuzzy = False
        self.classify = False
        self.classify_bank = False
        self.bank_paths = False
        self._hashtypes_missing = None # print only certain hashtypes

        self.sort_always = False
        self._default_weight = 100
        self._sort_weights = []

    def add_config(self, line):
        if line.startswith('#@nofuzzy'):
            self.disable_fuzzy = True

        if line.startswith('#@classify'):
            self.classify = True
        if line.startswith('#@classify-bank'): #implicit: sets the above
            self.classify_bank = True
        if line.startswith('#@classify-bank-path'): #implicit: sets the above
            self.classify_bank = True
            self.bank_paths = True

        if line.startswith('#@hashtypes-missing'):
            line = line.replace('#@hashtypes-missing', '')
            self._hashtypes_missing = [item.lower().strip() for item in line.split()]

        if line.startswith('#@sort-always'):
            self.sort_always = True
        if line.startswith('#@sort-weight') or line.startswith('#@sw'):
            self._add_sort_weight(line)

    def add_lines(self, lines):
        if self.disable_fuzzy:
            lines.append('#@nofuzzy')
        if self.classify_bank and self.bank_paths:
            lines.append('#@classify-bank-path')
        elif self.classify_bank:
            lines.append('#@classify-bank')
        elif self.classify:
            lines.append('#@classify')
        elif self._hashtypes_missing:
            lines.append('#@hashtypes-missing ' + ' '.join(self._hashtypes_missing))

    def skip_hastype(self, hashtype):
        return self._hashtypes_missing and hashtype not in self._hashtypes_missing


    # TODO maybe generate again when cleaning wwnames

    # defined sorting weight, where higher = lower priority (0=top, 100=default, 999=lowest). examples:
    #  group=value 10           # exact match
    #  group*=value* 20         # partial match
    #  group=- 999              # by default "any" has highest
    #  value 20                 # same as *=value
    #
    def _add_sort_weight(self, line):
        line = line.strip()
        elems = line.split(" ")
        if len(elems) != 3:
            logging.info("names: ignored weight %s", line )
            return
        match = elems[1]
        weight = elems[2]
        if not weight.isnumeric():
            logging.info("names: ignored weight %s", line )
            return

        if '*' == match:
            self._default_weight = weight
        else:
            if '=' in match:
                gv = match.split("=")
                g_wr = self._get_weight_regex(gv[0])
                v_wr = self._get_weight_regex(gv[1])
                item = (g_wr, v_wr, weight)
            else:
                v_wr = self._get_weight_regex(match)
                item = (None, v_wr, weight)
            self._sort_weights.append(item)

    def _get_weight_regex(self, text_in):
        if '*' in text_in:
            replaces = { '(':'\(', ')':'\)', '[':'\[', ']':'\]', '.':'\.', '*':'.*?' }
            regex_in = text_in
            for key, val in replaces.items():
                regex_in = regex_in.replace(key, val)
            regex = re.compile(regex_in, re.IGNORECASE)
        else:
            regex = re.compile(re.escape(text_in), re.IGNORECASE)
        return regex

    def get_weight(self, groupname, valuename):
        for g_wr, v_wr, weight in self._sort_weights:
            if not g_wr:
                if v_wr.match(valuename):
                    return weight
            else:
                if g_wr.match(groupname) and v_wr.match(valuename):
                    return weight

        if valuename == '-': #any usually goes first, unless overwritten
            return 0
        return self._default_weight
