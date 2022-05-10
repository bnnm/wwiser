import logging, os
from .render import wnode_source

# Moves 123.wem to /txtp/wem/123.wem, or 123.ogg/logg to /txtp/wem/123.logg if alt_exts is set

class Mover(object):
    def __init__(self, txtpcache):
        self._txtpcache = txtpcache
        self._moved_sources = {}


    def move_wems(self, nodes):
        if not nodes:
            return
        for node in nodes:
            self.move_wem(node)

    def move_wem(self, node):
        if not node:
            return

        source = wnode_source.AkBankSource(node, None)
        if not source or not source.tid: #?
            return
        if source.tid in self._moved_sources:
            return
        if source.plugin_external or source.plugin_id: #not audio:
            return
        if source.internal and not self._txtpcache.bnkskip:
            return

        self._moved_sources[source.tid] = True #skip dupes

        dir = self._txtpcache.get_txtp_dir()
        if self._txtpcache.lang:
            dir += source.subdir()

        nroot = node.get_root()
        in_dir = nroot.get_path()
        out_dir = self._txtpcache.get_basepath(node)

        in_name, out_name = self._get_names(source, in_dir, out_dir, dir)

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
                in_dir = self._txtpcache.get_basepath(node)
                in_name, out_name = self._get_names(source, in_dir, out_dir, dir)
                wem_exists = os.path.exists(in_name)

        if not wem_exists:
            logging.info("generator: cannot move %s (file not found) / %s", in_name, bank)
            return

        #todo: with alt-exts maybe could keep case, ex .OGG to .LOGG (how?)
        os.rename(in_name, out_name)
        logging.debug("generator: moved %s / %s", in_name, bank)

        return

    def _get_names(self, source, in_dir, out_dir, dir):
        if dir:
            out_dir = os.path.join(out_dir, dir)
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
