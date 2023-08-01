
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
    def __init__(self, fixed=False, zeropad=None):
        self.fixed = fixed
        self.zeropad = zeropad

    def format(self, type=None, value=None):
        if value is None:
            raise ValueError("formatter: value not set")
        if type is None:
            raise ValueError("formatter: type not set")

        format = HEX_FORMATS.get(type, None) #doubles as a "is int" check
        if format is None:
            return str(value)

        if value < 0:
            return "%i" % (value)

        if not self.fixed and not self.zeropad:
            return "0x%02X" % (value)

        if self.zeropad:
            format = "0x%0" + str(self.zeropad) + "X"

        return format % (value)

class FormatterLUT(object):
    def __init__(self, enum, zeropad=None):
        self.enum = enum
        self.fmt = FormatterHex(zeropad=zeropad)


    def format(self, type=None, value=None):
        if value is None:
            raise ValueError("formatter: value not set")
        if type is None:
            raise ValueError("formatter: type not set")

        description = " [%s]" % self.enum.get(value, "?")

        return self.fmt.format(type, value) + description

    def get(self, val):
        return self.enum.get(val)

CHANNEL_FORMATS = {
    (1 << 0):  "FL", # front left
    (1 << 1):  "FR", # front right
    (1 << 2):  "FC", # front center
    (1 << 3):  "LFE", # low frequency effects
    (1 << 4):  "BL", # back left
    (1 << 5):  "BR", # back right
    (1 << 6):  "FLC", # front left center
    (1 << 7):  "FRC", # front right center
    (1 << 8):  "BC", # back center
    (1 << 9):  "SL", # side left
    (1 << 10): "SR", # side right

    (1 << 11): "TC", # top center
    (1 << 12): "TFL", # top front left
    (1 << 13): "TFC", # top front center
    (1 << 14): "TFR", # top front right
    (1 << 15): "TBL", # top back left
    (1 << 16): "TBC", # top back center
    (1 << 17): "TBR", # top back left
}

class FormatterChannelConfig(object):
    def __init__(self):
        self.fmt = FormatterHex()

    def format(self, type=None, value=None):
        if value is None:
            raise ValueError("formatter: value not set")
        #if type is None:
        #    raise ValueError("formatter: type not set")

        mapping = ""
        for i in range(0, 32):
            bitmask = (1<<i)
            if value & bitmask:
                mapping += "%s " % (CHANNEL_FORMATS.get(bitmask, "?"))

        if not mapping:
            mapping = "None"

        return "0x%05X [%s]" % (value, mapping.strip())
