
#class FormatterStandard(object):
#    def __init__(self):
#        pass
#
#    def format(self, type=None, value=None):
#        if self.value is None:
#            raise ValueError("formatter: value not set")
#        return str(self.value)

HEX_FORMATS = {
   'u64': "0x%16X",
   'u32': "0x%08X",
   'u16': "0x%04X",
   'u8':  "0x%02X",
   'var': "0x%02X",
   'gap': "0x%02X",
}

class FormatterHex(object):
    def __init__(self, fixed=False):
        self.fixed = fixed

    def format(self, type=None, value=None):
        if value is None:
            raise ValueError("formatter: value not set")
        if type is None:
            raise ValueError("formatter: type not set")

        format = HEX_FORMATS.get(type, None)
        if format is None:
            return str(value)

        if value < 0:
            return "%i" % (value)

        if not self.fixed:
            return "0x%02X" % (value)

        format = HEX_FORMATS.get(type, None)
        return format % (value)


class FormatterLUT(object):
    def __init__(self, enum):
        self.enum = enum
        self.fmt = FormatterHex()


    def format(self, type=None, value=None):
        if value is None:
            raise ValueError("formatter: value not set")
        if type is None:
            raise ValueError("formatter: type not set")

        description = " [%s]" % self.enum.get(value, "?")

        return self.fmt.format(type, value) + description

