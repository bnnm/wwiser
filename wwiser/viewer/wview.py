import logging, random, threading
import webbrowser, http, http.server, socketserver
from urllib import parse

from . import wtemplate, wloader, wmarkdown


DEFAULT_PORT = 55123
#URL_BASE = 'http://localhost:%i/'
URL_MAIN = 'wwiser'


#******************************************************************************
# Dumb web server to serve a simple html visualizer tool. Doesn't use flask/jinja/fancy stuff
# for compatibility with most standard pythons and since we only need a handful of features.

class Viewer(object):

    def __init__(self, parser):
        self.parser = parser
        self.port = None
        self._httpd = None
        self._thread = None

    def _serve(self):
        try:
            self.open()
            logging.info("viewer: starting on port %i" % (self.port))
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            raise
        except Exception:
            logging.error("viewer: server closed")
            raise


    def start(self, port=DEFAULT_PORT, blocking=True):
        if self._httpd:
            self.open()
            return

        if not port: #None or 0
            port = random.randint(50080,59080)

        self.port = port
        self.init = True

        #http.server.SimpleHTTPRequestHandler
        #ViewerHandler
        #handler = ViewerHandler
        handler = HandlerFactory(self.parser)

        #http.socketserver.TCPServer
        #http.server.HTTPServer
        #ThreadedHTTPServer
        server = ThreadedHTTPServer

        address = ('localhost', port)

        self._httpd = server(address, handler)
        if blocking:
            try:
                self._serve()
            except KeyboardInterrupt:
                pass
            #finally: #external
            #    self.stop()
        else:
                self._thread = threading.Thread(target = self._serve)
                self._thread.daemon = True
                self._thread.start()


    def stop(self):
        if self._httpd:
            self._httpd.shutdown()
            self._httpd = None

        if self._thread:
            self._thread.join()
            self._thread = None

        logging.info("viewer: stopped")

    def open(self):
        base_url = 'http://localhost:%i/%s' % (self.port, URL_MAIN)
        logging.info("viewer: opening %s" % (base_url))
        webbrowser.open(base_url)

#******************************************************************************

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    pass

class NodePrinter(object):
    TEMPLATE_DEFAULT = 'unknown'
    TEMPLATE_NODENAMES_WITH_MAINNAMES = ['object'] #to ignore field names

    def __init__(self):
        self.stopped_nodes = {}
        self.templates = {}

    def _get_template_base(self, name):
        if not name:
            return None

        if name not in self.templates:
            res = wloader.Loader.get_resource('resources/templates/%s.tpl' % (name))
            if not res:
                tpl = None
            else:
                tpl = wtemplate.Template(res.decode())
            self.templates[name] = tpl #name is registered, but no template associated
        return self.templates[name]

    # get a suitable template: CAkSound (mainname) > object (nodename > unknown (default)
    def _get_template(self, mainname, nodename):

        if nodename is self.TEMPLATE_NODENAMES_WITH_MAINNAMES:
            tpl = self._get_template_base("%s-%s" % (nodename, mainname))
            if tpl:
                return tpl

        tpl = self._get_template_base(nodename)
        if tpl:
            return tpl

        tpl = self._get_template_base(self.TEMPLATE_DEFAULT)
        if tpl:
            return tpl

        raise ValueError('no template found')

    def _is_stop(self, nodename, attrs):
        #meh, improve

        if not self.stopper:
            return False

        stop_nodename = self.stopper['nodename']
        if not stop_nodename == nodename:
            return False

        stop_attrs = self.stopper['attrs']
        if stop_attrs:
            for key in stop_attrs.keys():
                if not key in attrs or stop_attrs[key] != attrs[key]:
                    return False

        return True

    #meh, use list join
    def _print_node(self, node, stop=False):
        nodeid = id(node)
        nodename = node.get_nodename()
        name = node.get_name()
        attrs = node.get_attrs()
        children = node.get_children()
        body = ""
        extra = ""

        if stop:
            extra = 'hidden js-load-node %s' % (attrs['name'])
            self.stopped_nodes[nodeid] = node

        stop_children = self._is_stop(nodename, attrs)
        if children and not stop:
            msgs = []
            for subnode in children:
                msg = self._print_node(subnode, stop=stop_children)
                msgs.append(msg)
            body = body.join(msgs)

        tpl = self._get_template(name, nodename)
        msg = tpl.render(id=nodeid, attrs=attrs, body=body, extra=extra)
        return msg

    def write_bank(self, node, all):
        # writes node + immediate children until conditions
        # we want to show the HIRC list, but not the objects so the browser can probably handle
        # the amount of DOM nodes (maybe should add a limit of results + "load more" too)
        if all:
            self.stopper = None
        else:
            name = 'listLoadedItem'
            self.stopper = {
                'nodename': 'list',
                'attrs': {'name': name},
            }
        msg = self._print_node(node)
        return msg

    def write_node(self, nodeid):
        self.stopper = None
        # find by id and never stop
        node = self.stopped_nodes[nodeid]
        msg = self._print_node(node)
        return msg

#******************************************************************************

class ViewerHandler(http.server.BaseHTTPRequestHandler):

    #?
    #def __init__(self, *args, **kwargs):
    #    self._parser = None
    #    self._printer = None
    #    super().__init__(*args, **kwargs)

    #**************************************************************************
    # OVERRIDES

    def do_GET(self):
        dispatch = {
            '/test': self.do_test,
            '/wwiser': self.do_main,
            '/load-banks': self.do_load_banks,
            '/load-node': self.do_load_node,
            '/load-docs': self.do_load_docs,
        }
        filetypes = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'text/javascript; charset=utf-8',
            '.png': 'image/png',
            '.ico': 'image/x-icon',
        }

        self.ppath = parse.urlparse(self.path)
        path = self.ppath.path

        action = dispatch.get(path)
        if action:
            action()
            return

        for filetype in filetypes.keys():
            if path.endswith(filetype):
                type = filetypes[filetype]
                self.do_file(path, type)
                return

        self.do_error()

    def do_POST(self):
        #content_length = int(self.headers['Content-Length'])
        #body = self.rfile.read(content_length)
        #...
        return

    def log_message(self, format, *args):
        #no logging
        return

    #**************************************************************************
    # WRITERS

    def _start_html(self):
        self._start('text/html; charset=utf-8')

    def _start_text(self):
        self._start('text/plain; charset=utf-8')

    def _start(self, type):
        self.send_response(200)
        self.send_header('Content-Type', type)
        self.end_headers()

    def _output(self, message):
        self.wfile.write(message)

    #**************************************************************************
    # GENERAL ACTIONS

    def do_file(self, path, type):
        # disallow only up to root?
        if '../' in path:
            raise ValueError("Path error")
        try:
            msg = wloader.Loader.get_resource('resources' + path)
            self._start(type)
            self._output(msg)
        except:
            #self.do_error()
            pass

    def do_error(self):
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b'404/Not Found')

    def do_test(self):
        ppath = self.ppath
        lines  = []

        lines.append('HEADERS')
        for key, value in sorted(self.headers.items()):
            lines.append("- {}={}".format(key, value))

        lines += [
            "INFO",
            "- thread={}".format(threading.currentThread().getName()),
            "- command={}".format(self.command),
            "- full_path={}".format(self.path),
            "- params={}".format(ppath.params),
            "- path={}".format(ppath.path),
            "- query={}".format(ppath.query),
            "- fragment={}".format(ppath.fragment),
            "- server_version={}".format(self.server_version),
            "- path={}".format(self.path),
            "- id={}".format(id(self)),
        ]

        tpl = wloader.Loader.get_resource('resources/templates/test.tpl').decode()
        t = wtemplate.Template(tpl)
        line = t.render(user='wwiser', testmap={'key':'val'})
        lines.append(line)

        msg = '\n'.join(lines)
        self._start_text()
        self._output(bytes(msg, 'utf-8'))

    #**************************************************************************
    # MAIN ACTIONS

    def do_main(self):
        msg = wloader.Loader.get_resource('resources/viewer.html')
        self._start_html()
        self._output(msg)

    def do_load_banks(self):
        params = parse.parse_qs(self.ppath.query)
        load_all = 'all' in params
        is_simple = 'simple' in params

        self._start_html()
        if is_simple:
            msg = ":("
            self._output(bytes(msg, 'utf-8'))
        else:
            for node in self._parser.get_banks():
                msg = self._printer.write_bank(node, load_all)
                self._output(bytes(msg, 'utf-8'))

    def do_load_node(self):
        params = parse.parse_qs(self.ppath.query)
        nodeid = int(params.get('id')[0])

        self._start_html()
        msg = self._printer.write_node(nodeid)
        self._output(bytes(msg, 'utf-8'))

    def do_load_docs(self):
        docnames = {
            'readme': 'README.md',
            'wwiser': 'WWISER.md',
        }

        params = parse.parse_qs(self.ppath.query)
        docname = docnames[params.get('doc')[0]]

        doc = wloader.Loader.get_resource('../../doc/'+docname) #src
        if not doc:
            doc = wloader.Loader.get_resource('../../'+docname) #base
        if not doc:
            doc = wloader.Loader.get_resource('resources/doc/'+docname) #pyz
        if not doc:
            raise ValueError("Can't find doc")

        text = doc.decode()
        md = wmarkdown.Markdown()
        msg = md.convert(text)

        self._start_html()
        self._output(bytes(msg, 'utf-8'))

def HandlerFactory(parser):
    #global, as init/handler is called on every request but it saves some stuff
    node_printer = NodePrinter()

    class CustomHandler(ViewerHandler):
        def __init__(self, *args, **kwargs):
             self._parser = parser
             self._printer = node_printer
             super(CustomHandler, self).__init__(*args, **kwargs)
    return CustomHandler
