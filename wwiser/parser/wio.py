import os, struct

class FileReader(object):

    def __init__(self, file):
        self.file = file
        self.be = False
        self._xorpad = None

        file.seek(0, os.SEEK_END)
        self.size = file.tell()
        file.seek(0, os.SEEK_SET)

    #def _read_buf(self, offset, type, size):
    #    elem = self.buf[offset:offset+size]
    #    return struct.unpack(type, elem)[0]

    def _check(self, elem, size):
        if not elem or len(elem) != size:
            raise ReaderError("can't read requested 0x%x bytes at 0x%x" % (size, self.current()))

    def __read(self, offset, type, size):
        if offset is not None:
            self.file.seek(offset, os.SEEK_SET)
        elem = self.file.read(size)
        if self._xorpad:
            elem = self.__unxor(elem, size)

        self._check(elem, size)

        return struct.unpack(type, elem)[0]

    def __read_string(self, offset, size):
        if offset is not None:
            self.file.seek(offset, os.SEEK_SET)
        if size == 0:
            return ""
        elem = self.file.read(size)
        self._check(elem, size)

        elem = bytes(elem) #force
        #remove c-string null terminator, .decode() retains it
        if elem[-1] == 0:
            elem = elem[:-1]
        text = elem.decode('UTF-8')
        return text

    def __bytes(self, offset, size):
        if offset is not None:
            self.file.seek(offset, os.SEEK_SET)
        elem = self.file.read(size)
        self._check(elem, size)

        elem = bytes(elem) #force
        return elem

    def __unxor(self, elem, size):
        offset = self.current() - size
        xorpad_len = len(self._xorpad)
        if offset >= xorpad_len:
            return elem

        max = offset + size
        if max > xorpad_len:
            max = xorpad_len

        elem = bytearray(elem)
        for i in range(offset, max):
            xor = self._xorpad[i]
            elem[i - offset] ^= xor
        return elem

    def d64le(self, offset = None):
        return self.__read(offset, '<d', 8)

    def d64be(self, offset = None):
        return self.__read(offset, '>d', 8)

    def d64(self, offset = None):
        if self.be:
            return self.d64be(offset)
        else:
            return self.d64le(offset)

    def f32le(self, offset = None):
        return self.__read(offset, '<f', 4)

    def f32be(self, offset = None):
        return self.__read(offset, '>f', 4)

    def f32(self, offset = None):
        if self.be:
            return self.f32be(offset)
        else:
            return self.f32le(offset)

    def s64le(self, offset = None):
        return self.__read(offset, '<q', 8)

    def s64be(self, offset = None):
        return self.__read(offset, '>q', 8)

    def u64le(self, offset = None):
        return self.__read(offset, '<Q', 8)

    def u64be(self, offset = None):
        return self.__read(offset, '>Q', 8)

    def s64(self, offset = None):
        if self.be:
            return self.s64be(offset)
        else:
            return self.s64le(offset)

    def u64(self, offset = None):
        if self.be:
            return self.u64be(offset)
        else:
            return self.u64le(offset)

    def s32le(self, offset = None):
        return self.__read(offset, '<i', 4)

    def s32be(self, offset = None):
        return self.__read(offset, '>i', 4)

    def u32le(self, offset = None):
        return self.__read(offset, '<I', 4)

    def u32be(self, offset = None):
        return self.__read(offset, '>I', 4)

    def s32(self, offset = None):
        if self.be:
            return self.s32be(offset)
        else:
            return self.s32le(offset)

    def u32(self, offset = None):
        if self.be:
            return self.u32be(offset)
        else:
            return self.u32le(offset)

    def s16le(self, offset = None):
        return self.__read(offset, '<h', 2)

    def s16be(self, offset = None):
        return self.__read(offset, '>h', 2)

    def s16(self, offset = None):
        if self.be:
            return self.s16be(offset)
        else:
            return self.s16le(offset)

    def u16le(self, offset = None):
        return self.__read(offset, '<H', 2)

    def u16be(self, offset = None):
        return self.__read(offset, '>H', 2)

    def u16(self, offset = None):
        if self.be:
            return self.u16be(offset)
        else:
            return self.u16le(offset)

    def s8(self, offset = None):
        return self.__read(offset, 'b', 1)

    def u8(self, offset = None):
        return self.__read(offset, 'B', 1)

    def str(self, size, offset = None):
        return self.__read_string(offset, size)

    def fourcc(self, offset = None):
        #as bytes rather than string to avoid failures on bad data
        return self.__bytes(offset, 4)

    def gap(self, bytes):
        offset_before = self.current()
        self.skip(bytes)
        offset_after = self.current()
        if offset_before + bytes != offset_after or offset_after > self.size:
            raise ReaderError("can't skip requested 0x%x bytes at 0x%x" % (bytes, self.current()))

    def seek(self, offset):
        self.file.seek(offset, os.SEEK_SET)

    def skip(self, bytes):
        self.file.seek(bytes, os.SEEK_CUR)

    def current(self):
        return self.file.tell()

    def get_size(self):
        return self.size

    def guess_endian32(self, offset):
        current = self.file.tell()
        var_le = self.u32le(offset)
        var_be = self.u32be(offset)

        if var_le > var_be:
            self.be = True
        else:
            self.be = False
        self.file.seek(current, os.SEEK_SET)

    def get_endian_big(self):
        return self.be

    def set_endian(self, big_endian):
        self.be = big_endian

    def is_eof(self):
        return self.current() >= self.size

    def get_path(self):
        return os.path.dirname(self.file.name)

    def get_filename(self):
        return os.path.basename(self.file.name)

    def set_xorpad(self, xorpad):
        self._xorpad = xorpad

class ReaderError(Exception):
    def __init__(self, msg):
        super(ReaderError, self).__init__(msg)
