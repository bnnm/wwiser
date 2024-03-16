import  re

# Renames .txtp to other names.
# Used to  simplify repetitive prefixes like "play_bgm (BGM_TYPE_MUSIC=BGM_TYPE_M01)" > play_bgm (MUSIC=M01)
# Contains a list loaded of rename stems, when applies to final txtp.
# Also deletes unwanted .txtp by using the <skip> flag.
# examples:
# "(BGM_:(": changes "play_BGM (BGM_MUSIC=M01)" to "play_BGM (MUSIC=M01)"
# "\\((.+?)=\\1_:(\\1=": changes "play_BGM (BGM_MUSIC=BGM_MUSIC_M01)" to "play_BGM (BGM_MUSIC=M01)"


class TxtpRenamer(object):
    SKIP_FLAG = '<skip>'

    def __init__(self):
        self._items = []
        self._has_skips = False
        self.skip = False

    def add(self, items):
        if not items:
            return
        for item in items:
            parts = item.split(":")
            if len(parts) != 2:
                continue

            text_in = parts[0]
            text_out = parts[1]
            regex = None
            if any(item in text_in for item in ['*','+','^','$', '.']):
                # full regex
                regex_in = text_in

                # not sure how to guess if regex was properly parsed or not
                #replaces = { '(':'\(', ')':'\)', '[':'\[', ']':'\]', '.':'\.', '*':'.*?' }
                #for key, val in replaces.items():
                #    regex_in = regex_in.replace(key, val)
                regex = re.compile(regex_in, re.IGNORECASE)
            else:
                # simple text
                regex = re.compile(re.escape(text_in), re.IGNORECASE)

            skip = text_out == self.SKIP_FLAG
            if skip:
                self._has_skips = True

            item = (text_in, text_out, skip, regex)
            self._items.append(item)
        return

    def apply_renames(self, name):
        if not self._items:
            return name

        # special "skip this txtp if rename matches" flag (for variables), lasts until next call
        # repeated at the end b/c it should go after cleanup (extra spaces) and final name
        self.skip = False


        # base renames
        for text_in, text_out, skip, regex in self._items:
            if skip and (regex and regex.match(name) or text_in in name):
                self.skip = True
                return name

            if regex:
                name = regex.sub(text_out, name)
            else:
                # not used at the moment (uses regex to handle case insensitiveness)
                name = name.replace(text_in, text_out)

        # clean extra stuff after cleanup            
        replaces = { '(=':'(', '[=':'[', '=)':')', '=]':']', '()':'', '[]':'' }
        for key, val in replaces.items():
            name = name.replace(key, val)
        while '  ' in name:
            name = name.replace("  ", " ")

        name.strip()

        # skips after cleaning up
        if self._has_skips:
            for text_in, text_out, skip, regex in self._items:
                if skip and (regex and regex.match(name) or text_in in name):
                    self.skip = True
                    return name

        return name
