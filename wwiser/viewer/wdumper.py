import logging
from . import wloader
from ..parser import wmodel


TYPE_TXT = 'txt'
TYPE_XSL = 'xsl'
TYPE_XSL_SMALLER = 'xsl_s'
TYPE_XML = 'xml'
TYPE_EMPTY = 'empty'
TYPE_NONE = 'none'


class DumpPrinter(object):
    attr_format = { 
        'offset':"%08x", 'size':"0x%x"
    }
    node_smaller = {
        'object':'obj', 'field':'fld', 'list':'lst'
    }
    attr_smaller = { 
        'offset':'of', 'type':'ty', 'name':'na', 'value':'va', 'valuefmt':'vf',
        'hashname':'hn', 'guidname':'gn', 'objpath':'op', 'path':'pa',
        'index':'ix', 'count':'co', 'size':'si', 'message':'me',
    }
    attr_hide = { 
        'offset'
    }

    def __init__(self, banks, type, name):
        self._banks = banks
        self._type = type
        self._name = name
        self._file = None
        self._formatted = False
        self._smaller = False
        self._hide = False


    def dump(self):
        if   self._type == TYPE_TXT:
            self.write_txt()
        elif self._type == TYPE_XML:
            self.write_xml()
        elif self._type == TYPE_XSL:
            self.write_xsl()
        elif self._type == TYPE_XSL_SMALLER:
            self.write_xsl_smaller()
        elif self._type == TYPE_EMPTY:
            self.write_empty()
        elif self._type == TYPE_NONE:
            pass
        else:
            raise ValueError("unknown type: " + self._type)

    def _make_name(self, extension):
        outname  = self._name
        outname += extension
        return outname

    def write_txt(self):
        outname  = self._make_name(".txt")
        self._write(outname, self._print_txt)

    def write_xml(self):
        outname  = self._make_name(".xml")
        self._write(outname, self._print_xml)

    def write_xsl(self):
        self._formatted = True
        self.write_xml()

    def write_xsl_smaller(self):
        self._smaller = True
        self._hide = True
        self.write_xsl()

    def _write(self, outname, callback):
        if not self._banks: #no banks loaded
            return
        logging.info("dumper: writting %s" % (outname))
        #it's possible to set 'buffering' on open, but doesn't seem to have any positive effect
        with open(outname, 'w', encoding='utf-8') as outfile:
            self._file = outfile
            callback()
            self._file = None
        logging.info("dumper: done")

    def write_empty(self):
        if not self._banks: #no banks loaded
            return
        logging.info("dumper: processing empty type")

        # making empty "files" is a way to force the whole tree to read names, since by
        # default they are only loaded on demand, but full list is needed in some cases
        for bank in self._banks:
            self._print_empty_node(bank)

        logging.info("dumper: done")

    #--------------------------------------------------------------------------

    def _print_empty_node(self, node):
        __ = node.get_attrs() #forces names!
        children = node.get_children()

        if children:
            for subnode in children:
                self._print_empty_node(subnode)

    def _print_xml(self):
        #stylesheet handling could be improved, not sure
        if self._formatted:
            text = wloader.Loader.get_resource_text('resources/stylesheet.1.xsl')
            self._file.write(text)

        # may reimplement this as a stack-based printer rather than recursive calls
        # but time savings are not too big (~3s for bigger files)
        for bank in self._banks:
            self._print_xml_node(bank, 0)

        if self._formatted:
            text = wloader.Loader.get_resource_text('resources/stylesheet.2.xsl')
            self._file.write(text)

    def _print_xml_node(self, node, depth):
        just = '\t' * depth

        nodename = node.get_nodename()
        attrs = node.get_attrs().items()
        children = node.get_children()
        #text = node.get_text()
        has_children = children and len(children) > 0

        line = ""
        for key, val in attrs:
            if self._hide and key in self.attr_hide:
                continue
            if self._formatted and key in self.attr_format:
                strval = self.attr_format[key] % val
            else:
                strval = str(val)
            for chr, rpl in [('&','&amp;'), ('"','&quot;'), ('\'','&apos;'), ('<','&lt;'), ('>','&gt;')]:
                strval = strval.replace(chr, rpl)
            if self._smaller and key in self.attr_smaller:
                key = self.attr_smaller[key]
            line += " %s=\"%s\"" % (key, strval)

        if self._smaller and nodename in self.node_smaller:
            nodename = self.node_smaller[nodename]

        if not has_children:
            line = "%s<%s%s/>\n" % (just, nodename, line)
            self._file.write(line)
        else:
            line = "%s<%s%s>\n" % (just, nodename, line)
            self._file.write(line)

            depth += 1
            for subnode in children:
                self._print_xml_node(subnode, depth)

            line = "%s</%s>\n" % (just, nodename)
            self._file.write(line)


    def _print_txt(self):
        for bank in self._banks:
            self._print_txt_node(bank, 0, 0)

    def _print_txt_node(self, node, depth, index):
        just = ''.ljust(depth)
        ojust = ''.ljust(8)

        #nodename = node.get_nodename()
        attrs = node.get_attrs()
        children = node.get_children()
        #text = node.get_text()
        has_children = children and len(children) > 0

        line = None
        if   isinstance(node, wmodel.NodeRoot):
            type = "bank".ljust(4)
            version = attrs['version']
            filename = attrs['filename']
            line = "%s  %s%s v%i %s" % (ojust, just, type, version, filename)

        elif isinstance(node, wmodel.NodeObject):
            type = "obj".ljust(4)
            name = attrs['name']
            if index is not None: #>=0
                line = "%s  %s%s %s[%i]" % (ojust, just, type, name, index)
            else:
                line = "%s  %s%s %s" % (ojust, just, type, name)

        elif isinstance(node, wmodel.NodeList):
            type = "lst".ljust(4)
            name = attrs['name']
            line = "%s  %s%s %s" % (ojust, just, type, name)

        elif isinstance(node, wmodel.NodeField):
            offset = attrs.get('offset')
            type = attrs['type'].ljust(4)
            name = attrs['name']
            text = attrs.get('valuefmt', attrs['value'])

            if offset:
                offset = "%08x" % (offset)
            else:
                offset = ''
            line = "%s  %s%s %s = %s" % (offset, just, type, name, text)

            keys = ['hashname', 'guidname', 'objpath', 'path']
            for key in keys:
                value = attrs.get(key, None)
                if value:
                    line += " (%s)" % (value)

        elif isinstance(node, wmodel.NodeSkip):
            offset = attrs['offset']
            size = attrs['size']
            line = "%08x  %s(skipped @0x%x)" % (offset, just, size)

        elif isinstance(node, wmodel.NodeError):
            message = attrs['message']
            line = "%s  %s**error: %s" % (ojust, just, message)

        if line is not None:
            self._file.write(line + '\n')
            depth += 3


        if has_children:
            if   isinstance(node, wmodel.NodeList):
                for index, subnode in enumerate(children):
                    self._print_txt_node(subnode, depth, index)
            else:
                for subnode in children:
                    self._print_txt_node(subnode, depth, None)
