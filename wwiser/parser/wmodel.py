import os
from collections import OrderedDict
from . import wdefs, wfinder

#maybe should be in some enum?
TYPE_4CC = '4cc'
TYPE_D64 = 'd64'
TYPE_S64 = 's64'
TYPE_U64 = 'u64'
TYPE_S32 = 's32'
TYPE_U32 = 'u32'
TYPE_F32 = 'f32'
TYPE_SID = 'sid'
TYPE_TID = 'tid'
TYPE_UNI = 'uni'
TYPE_S16 = 's16'
TYPE_U16 = 'u16'
TYPE_S8  = 's8'
TYPE_U8  = 'u8'
TYPE_VAR = 'var'
TYPE_GAP = 'gap'
TYPE_STR = 'str'
TYPE_STZ = 'stz'

TYPES_SIZE = {
    TYPE_D64: 8,
    TYPE_S64: 8,
    TYPE_U64: 8,
    TYPE_4CC: 4,
    TYPE_S32: 4,
    TYPE_U32: 4,
    TYPE_F32: 4,
    TYPE_SID: 4,
    TYPE_TID: 4,
    TYPE_UNI: 4,
    TYPE_S16: 2,
    TYPE_U16: 2,
    TYPE_S8: 1,
    TYPE_U8: 1,
    TYPE_VAR: 1, #variable, min 1
    TYPE_GAP: -1, #variable
    TYPE_STR: -1, #variable
    TYPE_STZ: -1, #variable
}
#not used ATM, just some (rather obvious) doc
TYPES_INFO = {
    TYPE_SID: "ShortID (uint32_t)",
    TYPE_TID: "target ShortID (uint32_t)", #same thing but for easier understanding of output
    TYPE_UNI: "union (float / int32_t)",
    TYPE_D64: "double",
    TYPE_F32: "float",
    TYPE_4CC: "FourCC",
    TYPE_S64: "int64_t",
    TYPE_U64: "uint64_t",
    TYPE_S32: "int32_t",
    TYPE_U32: "uint32_t",
    TYPE_S16: "int16_t",
    TYPE_U16: "uint16_t",
    TYPE_S8 : "int8_t",
    TYPE_U8 : "uint8_t",
    TYPE_VAR: "variable size", #u8/u16/u32
    TYPE_GAP: "byte gap",
    TYPE_STR: "string",
    TYPE_STZ: "string (null-terminated)",
}


# base parent class for nodes
class NodeElement(object):
    __slots__ = ['__nodename', '_parent', '_children', '_root', '_error_count', '_skip_count', '_omax']

    def __init__(self, parent, nodename):
        self.__nodename = nodename
        self._parent = parent
        self._children = None #lazy init, reduces some MBs of memory when we can have lots of nodes
        if parent is None:
            self._root = self
        else:
            self._root = parent._root
        self._error_count = 0
        self._skip_count = 0

        # max readable offset, by default same as parent
        # may be overwritten by subclasses
        self._omax = None
        if parent is not None:
            self._omax = parent._omax

    # *** build helpers ***

    def append(self, node):
        if not node:
            return
        if self._children is None:
            self._children = [] #lazy init!
        self._children.append(node)

    def add_error(self, msg):
        error = NodeError(self, msg)
        self.append(error)

    # *** external access ***

    def get_attrs(self): #generic access to node's attributes
        return {} #use throw away dicts

    def get_attr(self, attr): #access to node's attribute (faster than get_attrs)
        return None

    def get_nodename(self):
        if self.__nodename is not None:
            return self.__nodename
        return self.__class__.__name__

    def get_parent(self):
        return self._parent

    def get_children(self):
        #if self._children is None:
        #    self._children = [] #lazy init!
        return self._children

    def get_root(self):
        return self._root

    def get_name(self):
        return None


    def get_error_count(self):
        return self._error_count

    def get_skip_count(self):
        return self._skip_count

    # *** external helpers ***

    def find(self, **args):
        return wfinder.NodeFinder(**args).find(self)

    def find1(self, **args):
        return wfinder.NodeFinder(**args).find1(self)

    def finds(self, **args):
        return wfinder.NodeFinder(**args).finds(self)


# root node with special definitions (represents a bank)
class NodeRoot(NodeElement):
    __slots__ = ['__r', '__filename', '__path', '_version', '_id', '_lang', '_feedback', '_custom', '_subversion', '_names', '_strings']

    def __init__(self, r, version=0):
        super(NodeRoot, self).__init__(None, 'root')
        self.__r = r
        self.__filename = r.get_filename()
        self.__path = r.get_path()
        self._version = version

        self._id = None
        self._subversion = None
        self._lang = False
        self._feedback = False
        self._custom = False
        self._names = None
        self._strings = []


    # *** inheritance ***

    def get_attrs(self):
        attrs = OrderedDict([
            ('filename', self.__filename),
            ('path', self.__path),
            ('version', self._version),
        ])
        return attrs

    # *** node helpers ***

    def node(self, name):
        obj = NodeObject(self, self.__r, name)
        self.append(obj)
        return obj

    # *** other (maybe could be some generic attrs) ***

    def get_bankname(self):
        # bank is usually hashed and used as bank's sid
        bankname = os.path.basename(self.__filename) #[:-4] #
        bankname = os.path.splitext(bankname)[0]
        return bankname

    def add_string(self, string):
        if not string:
            return
        self._strings.append(string)

    def get_strings(self):
        return self._strings

    def get_filename(self):
        return self.__filename

    def get_path(self):
        return self.__path

    def get_version(self):
        return self._version

    def set_version(self, version):
        self._version = version

    def get_id(self):
        return self._id

    def set_id(self, id):
        self._id = id

    def get_subversion(self):
        return self._subversion

    def set_subversion(self, subversion):
        self._subversion = subversion

    def set_lang(self, lang):
        self._lang = lang

    def get_lang(self):
        return self._lang

    def has_feedback(self):
        return self._feedback

    def set_feedback(self, feedback):
        self._feedback = feedback

    def is_custom(self):
        return self._custom

    def set_custom(self, flag):
        self._custom = flag

    def set_names(self, names):
        self._names = names

    def is_be(self):
        return self.__r.get_endian_big()


# logical node container of other nodes, with data reading helpers (represents a class)
class NodeObject(NodeElement):
    __slots__ = ['__r', '__name', 'lastval', '_index']

    def __init__(self, parent, r, name):
        super(NodeObject, self).__init__(parent, 'object')
        self.__r = r
        self.__name = name
        self._index = None
        self.lastval = None

    # *** inheritance ***

    def get_attrs(self):
        attrs = OrderedDict([
            ('name', self.__name),
        ])
        if self._index is not None:
            attrs['index'] = self._index
        return attrs

    def get_attr(self, attr):
        if attr == 'name':
            return self.__name
        if attr == 'index':
            return self._index
        return None

    def get_name(self):
        return self.__name

    # changes name, mainly to alter subclasses
    def set_name(self, name):
        self.__name = name

    def get_index(self):
        return self._index

    # *** node helpers ***

    def four(self, name):
        return self.field(TYPE_4CC, name)

    def sid(self, name):
        return self.field(TYPE_SID, name)

    def tid(self, name):
        return self.field(TYPE_TID, name)

    def uni(self, name):
        return self.field(TYPE_UNI, name)

    def var(self, name):
        return self.field(TYPE_VAR, name)

    def s64(self, name):
        return self.field(TYPE_S64, name)

    def u64(self, name):
        return self.field(TYPE_U64, name)

    def U64(self, name):
        return self.u64(name).fmt(wdefs.fmt_hex)

    def s32(self, name):
        return self.field(TYPE_S32, name)

    def u32(self, name):
        return self.field(TYPE_U32, name)

    def U32(self, name):
        return self.u32(name).fmt(wdefs.fmt_hex)

    def s16(self, name):
        return self.field(TYPE_S16, name)

    def u16(self, name):
        return self.field(TYPE_U16, name)

    def U16(self, name):
        return self.u16(name).fmt(wdefs.fmt_hex)

    def s8i(self, name):
        return self.field(TYPE_S8, name)

    def u8i(self, name):
        return self.field(TYPE_U8, name)

    def U8x(self, name):
        return self.u8i(name).fmt(wdefs.fmt_hex)

    def f32(self, name):
        return self.field(TYPE_F32, name)

    def d64(self, name):
        return self.field(TYPE_D64, name)

    def str(self, name, size):
        return self.field(TYPE_STR, name, size=size)

    def stz(self, name):
        return self.field(TYPE_STZ, name)

    def gap(self, name, size):
        return self.field(TYPE_GAP, name, size=size).fmt(wdefs.fmt_hex)

    def peek32(self):
        value = self.__r.u32()
        self.__r.skip(-4)
        return value

    # register new field and add value to object
    def field(self, type, name, value=None, size=None):
        r = self.__r

        offset = r.current()

        if self._omax:
            if size:
                read_size = size
            else:
                read_size = TYPES_SIZE.get(type, 0)
            if offset + read_size > self._omax:
                raise ParseError("error reading past object (offset %08x + read %x)" % (offset, read_size), self)

        if value is None:
            if   type == TYPE_4CC:
                value = r.fourcc()
            elif type == TYPE_S64:
                value = r.s64()
            elif type == TYPE_U64:
                value = r.u64()
            elif type == TYPE_S32:
                value = r.s32()
            elif type == TYPE_U32 or type == TYPE_SID or type == TYPE_TID:
                value = r.u32()
                if value == 0xFFFFFFFF:
                    value = -1 #clearly show (happens in rare cases)
            elif type == TYPE_S16:
                value = r.s16()
            elif type == TYPE_U16:
                value = r.u16()
            elif type == TYPE_S8:
                value = r.s8()
            elif type == TYPE_U8:
                value = r.u8()
                #if value == 0xFF:
                #    value = -1
            elif type == TYPE_F32:
                value = r.f32()
            elif type == TYPE_D64:
                value = r.d64()

            elif type == TYPE_STR:
                if size > 255:
                    raise ParseError("unlikely string size %i" % (size), self)
                else:
                    value = r.str(size)

            elif type == TYPE_GAP:
                r.gap(size)
                value = size

            elif type == TYPE_STZ:
                # sorry...
                stz = ""
                max = 0
                while True:
                    elem = r.s8()
                    if elem == 0 or elem < 0: #ASCII 128b only
                        break
                    stz += chr(elem)
                    max += 1
                    if max > 255: #arbitary max
                        raise ValueError("long string")
                value = stz

            elif type == TYPE_UNI:
                # union of f32+u32 determined by Wwise subclass, do some simple guessing instead
                # IEEE float uses upper 9 bits for the exponent, so high values must be floats
                value = r.u32()
                if value > 0x10000000:
                    r.skip(-4)
                    value = r.f32()

            elif type == TYPE_VAR:
                cur = r.u8()
                value = (cur & 0x7F)

                max = 0
                while (cur & 0x80) and max < 10:
                    cur = r.u8()
                    value = (value << 7) | (cur & 0x7F)
                    max += 1
                if max >= 10: #arbitary max
                    raise ValueError("unexpected variable loop count")
            else:
                raise ValueError("unknown field type " + type)

        # save field value for quick  repeated access
        self.lastval = value
        # originally each field could became a new property (obj.name=value)
        # but it's disabled to use slots and keep memory size down, plus it wasn't very useful
        #self.__dict__[name] = value

        # register new field as info
        child = NodeField(self, offset, type, name, value)
        self.append(child)

        return child

    # register and add a list node and return iterator with new nodes
    def list(self, name, subname, count):
        child = NodeList(self, name)
        self.append(child)

        # usually will fail by reading past object but in rare cases can generate too many fields
        if count > 0x30000: #arbitary max (seen ~178879 = 0x2BABF Cp2077)
            raise ParseError("unlikely count %s" % count, self)
        if subname is None:
            subname = name
        return NodeListIterator(child, self.__r, subname, count)

    # register a list with items
    def items(self, name, items):
        #child = NodeList(self, name)
        child = NodeObject(self, None, name)
        self.append(child)

        #adding item.index would modify the original list
        for item in items:
            child.append(item)
        return child

    # register and add existing list subelement
    #def list_node(self, name):
    #    if name not in self.__dict__:
    #        child = NodeList(self, name)
    #        self.__dict__[name] = child.get_children()
    #        #self.lastval = child.get_children()
    #        self.get_children().append(child)
    #
    #    obj = NodeObject(self, self.__r, name)
    #    self.__dict__[name].append(obj)
    #    #self.lastval = obj
    #    return obj

    def node(self, name):
        obj = NodeObject(self, self.__r, name)
        self.append(obj)
        #self.__dict__[name] = obj
        #self.lastval = obj
        return obj

    # *** other (chained) ***

    # sets max offset for this object based on current position and left data
    def omax(self, size_left):
        offset = self.__r.current()
        if self._omax and self._omax < offset + size_left:
            raise ParseError("object max size 0x%x + 0x%x over parent 0x%x" % (offset, size_left, self._omax), self)

        self._omax = offset + size_left
        return self

    # skips data up to object's max offset
    def consume(self):
        offset = self.__r.current()
        omax = self._omax
        if omax is None:
            raise ValueError("consume without size")

        to_skip = omax - offset

        if to_skip == 0:
            return
        if to_skip < 0:
            raise ValueError("wrong consume: offset=%x, omax=%x, to_skip=%x" % (offset, omax, to_skip))
        self.__r.gap(to_skip)
        self.append(NodeSkip(self, offset, to_skip))
        self.get_root()._skip_count += 1
        return self

    def offset_info(self):
        offset = self.__r.current()
        omax = self._omax

        #TODO improve
        return (omax, offset)


# simple subnode container (represents an array)
class NodeList(NodeElement):
    __slots__ = ['__name']

    def __init__(self, parent, name):
        super(NodeList, self).__init__(parent, 'list')
        self.__name = name

    # *** inheritance ***

    def get_attrs(self):
        count = 0
        if self._children:
            count = len(self._children)

        attrs = OrderedDict([
            ('name', self.__name),
            ('count', count),
        ])
        return attrs

    def get_attr(self, attr):
        if attr == 'name':
            return self.__name
        if attr == 'count':
            count = 0
            if self._children:
                count = len(self._children)
            return count
        return None

    def get_name(self):
        return self.__name


# semi-leaf node describing a physical data "field" (represents a primitive member)
class NodeField(NodeElement):
    __slots__ = ['__offset', '__type', '__name', '__value', '__fmt', '__hashtype', '__row']

    def __init__(self, parent, offset, type, name, value):
        super(NodeField, self).__init__(parent, 'field')
        self.__offset = offset
        self.__type = type
        self.__name = name
        self.__value = value
        self.__fmt = None
        self.__hashtype = False
        self.__row = None

    # *** inheritance ***

    def get_attrs(self):
        attrs = OrderedDict()
        if self.__offset:
            attrs['offset'] = self.__offset
        attrs['type'] = self.__type
        attrs['name'] = self.__name
        attrs['value'] = self.__value
        if self.__fmt:
            attrs['valuefmt'] = self.__fmt.format(self.__type, self.__value)

        if self.__type in [TYPE_SID, TYPE_TID]:
            row = self._get_namerow()
            if row:
                if row.hashname and self.__hashtype != wdefs.fnv_no:
                    attrs['hashname'] = row.hashname
                if row.guidname:
                    attrs['guidname'] = row.guidname
                if row.path:
                    attrs['path'] = row.path
                if row.objpath:
                    attrs['objpath'] = row.objpath

        return attrs

    def get_attr(self, attr):
        if attr == 'offset':
            return self.__offset
        if attr == 'type':
            return self.__type
        if attr == 'name':
            return self.__name
        if attr == 'value':
            return self.__value
        if attr == 'valuefmt':
            if self.__fmt:
                return self.__fmt.format(self.__type, self.__value)
            return None
        if attr == 'hashname':
            row = self._get_namerow()
            if row and row.hashname and self.__hashtype != wdefs.fnv_no:
                return row.hashname
            return None
        if attr == 'guidname': # and self.__row
            row = self._get_namerow()
            if row:
                return row.guidname
        return None

    def get_name(self):
        return self.__name

    def _get_namerow(self):
        # row in cache
        if self.__row is not None:
            return self.__row

        # signal "tried to load but no results" by default
        self.__row = False

        names = self.get_root()._names
        if names:
            row = names.get_namerow(self.__value, hashtype=self.__hashtype, node=self)
            if row:
                self.__row = row
        return self.__row

    # *** node helpers ***

    def bit(self, name, value, bit, mask=1, fmt=None):
        bitvalue = (value >> bit) & mask
        child = self.subfield('bit' + str(bit), name, bitvalue)
        if fmt:
            child.fmt(fmt)
        elif mask > 1:
            child.fmt(wdefs.fmt_hex)
        return self #to simplify chaining

    def u8i(self, name, value):
        return self.subfield(TYPE_U8, name, value)

    def U8x(self, name, value):
        return self.subfield(TYPE_U8, name, value).fmt(wdefs.fmt_hexfix)

    def u16(self, name, value):
        return self.subfield(TYPE_U16, name, value)

    def U16(self, name, value):
        return self.u16(name, value).fmt(wdefs.fmt_hexfix)

    def subfield(self, type, name, value):
        subfield = NodeField(self, None, type, name, value) #don't pass self.__offset
        self.append(subfield)
        return subfield

    # *** other (for chaining) ***

    # sets a value formatter
    def fmt(self, fmt):
        self.__fmt = fmt
        return self

    # sets parent object's max offset with current value
    def omax(self):
        return self.get_parent().omax(self.__value)

    # get parent alias
    def up(self):
        return self.get_parent()

    def value(self):
        return self.__value

    # field's ID comes from a FNV hashname
    def fnv(self, hashtype):
        self.__hashtype = hashtype
        return self


# leaf node that signals a portion of data skipped
class NodeSkip(NodeElement):
    __slots__ = ['__offset', '__size']

    def __init__(self, parent, offset, size):
        super(NodeSkip, self).__init__(parent, 'skip')
        self.__offset = offset
        self.__size = size

    # *** inheritance ***

    def get_attrs(self):
        attrs = OrderedDict([
            ('offset', self.__offset),
            ('size', self.__size),
        ])
        return attrs

# leaf node that signals some error in data
class NodeError(NodeElement):
    __slots__ = ['__msg']

    def __init__(self, parent, msg):
        super(NodeError, self).__init__(parent, 'error')
        self.__msg = msg

    # *** inheritance ***

    def get_attrs(self):
        attrs = OrderedDict([
            ('message', self.__msg),
        ])
        return attrs


# Iterator used to create new NodeObjects until count, if they don't exist.
# This delayed creation is needed b/c objs set current offset, and it only
# makes sense after previous object is first read
class NodeListIterator:
    __slots__ = ['__parent', '__r', '__subname', '__subname', '__index', '__count', '__list']

    def __init__(self, parent, r, subname, count):
        self.__parent = parent
        self.__r = r
        self.__subname = subname
        self.__index = 0
        self.__count = count

    def __iter__(self):
        self.__index = 0
        return self

    def _next(self): # for python2
        list = self.__parent.get_children()
        if list is None:
            list_len = -1
        else:
            list_len = len(list)

        if self.__index >= self.__count:
            raise StopIteration

        if self.__index < list_len:
            return list[self.__index]
        #if self.__index < len(self.__list):
        #    return self.__list[self.__index]

        obj = NodeObject(self.__parent, self.__r, self.__subname)
        obj._index = self.__index

        #self.__list.append(obj)
        self.__parent.append(obj)
        self.__index += 1
        return obj


    def next(self): # for python2
        return self._next()

    def __next__(self): # for python3
        return self._next()

    #pre-generate all (empty) objects, used when object's fields need to be read in weird order
    def preload(self):
        items = []
        for item in self:
            items.append(item)
        return items


class ParseError(Exception):
    def __init__(self, msg, obj):
        super(ParseError, self).__init__(msg)
        if obj is not None:
            obj.get_root()._error_count += 1
        pass


class VersionError(Exception):
    def __init__(self, msg, code=-1):
        super(VersionError, self).__init__(msg)
        self.msg = msg
        self.code = code

    def info(self):
        return (self.code, self.msg)
