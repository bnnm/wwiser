import logging, os
from .render import bnode_source

# Moves 123.wem to /txtp/wem/123.wem, or 123.ogg/logg to /txtp/wem/123.logg if alt_exts is set

_OBJECT_SOURCES = {
    'CAkSound': 'AkBankSourceData',
    'CAkMusicTrack': 'AkBankSourceData',
}


class Mover(object):
    def __init__(self, txtpcache):
        self._txtpcache = txtpcache
        self._nodes = []
        self._moved_sources = {}
        # conserve case stuff
        self._dirs = {}

    def add_node(self, node):
        hircname = node.get_name()
        node_name = _OBJECT_SOURCES.get(hircname)
        if node_name:
            nsources = node.finds(name=node_name)
            self._nodes.extend(nsources)

    def move_wems(self):
        if self._txtpcache.locator.is_auto_find():
            logging.info("mover: can't move wems when using autofind")
            return

        if not self._nodes:
            return
        for node in self._nodes:
            self._move_wem(node)

    def _move_wem(self, node):
        if not node:
            return

        source = bnode_source.AkBankSourceData(node, None)
        if not source or not source.tid: #?
            return
        if source.tid in self._moved_sources:
            return
        if source.plugin_external or source.plugin_id: #not audio:
            return
        if source.internal and not self._txtpcache.bnkskip:
            return

        self._moved_sources[source.tid] = True #skip dupes

        nroot = node.get_root()
        in_dir = nroot.get_path()
        out_dir = self._txtpcache.locator.get_wem_fullpath()

        if in_dir == out_dir:
            return

        in_name, out_name = self._get_names(source, in_dir, out_dir)

        if os.path.exists(out_name):
            if os.path.exists(in_name):
                logging.info("generator: cannot move %s (exists on output folder)", in_name)
            return

        bank = nroot.get_filename()
        wem_exists = os.path.exists(in_name)
        if not wem_exists:
            if self._txtpcache.alt_exts:
                # try as .logg
                in_name = "%s.%s" % (source.tid, source.extension_alt)
                in_name = os.path.join(in_dir, in_name)
                in_name = os.path.normpath(in_name)
                wem_exists = os.path.exists(in_name)

            elif in_dir != out_dir:
                # by default it tries in the bank's dir, but in case of lang banks may need to try in other banks' folder
                in_dir = self._txtpcache.locator.get_root_fullpath()
                in_name, out_name = self._get_names(source, in_dir, out_dir)
                wem_exists = os.path.exists(in_name)

        if not wem_exists:
            logging.info("generator: cannot move %s (file not found) / %s", in_name, bank)
            return

        # it's nice to keep original extension case (also for case-sensitive OSs)
        in_name, out_name = self.fix_case(in_name, out_name)

        os.rename(in_name, out_name)
        logging.debug("generator: moved %s / %s", in_name, bank)

        return

    def fix_case(self, in_name, out_name):
        dir = os.path.dirname(in_name) 
        name = os.path.basename(in_name)
        if not dir:
            dir = '.'

        if dir not in self._dirs:
            self._dirs[dir] = os.listdir(dir)
        items = self._dirs[dir]

        # find OS's file as see if it's named differently
        name_lw = name.lower()
        
        for item in items:
            if name_lw.endswith(item.lower()):
                if name != item:
                    _, item_in_ext = os.path.splitext(item)
                    item_out_ext = item_in_ext

                    in_base, _ = os.path.splitext(in_name)
                    _, in_ext = os.path.splitext(in_name)
                    
                    out_base, _ = os.path.splitext(out_name)
                    _, out_ext = os.path.splitext(out_name)

                    if in_ext != out_ext and out_ext.lower().startswith('.l'): #localized
                        item_out_ext = '.L' + item_out_ext[1:]

                    in_name = in_base + item_in_ext
                    out_name = out_base + item_out_ext
                break

        return (in_name, out_name)

    def _get_names(self, source, in_dir, out_dir):
        os.makedirs(out_dir, exist_ok=True)

        in_extension = source.extension
        out_extension = source.extension
        if self._txtpcache.alt_exts:
            #in_extension = source.extension_alt #handled below
            out_extension = source.extension_alt

        in_name = "%s.%s" % (source.tid, in_extension)
        in_name = os.path.join(in_dir, in_name)
        in_name = os.path.normpath(in_name)
        out_name = "%s.%s" % (source.tid, out_extension)
        out_name = os.path.join(out_dir, out_name)
        out_name = os.path.normpath(out_name)
        return (in_name, out_name)
