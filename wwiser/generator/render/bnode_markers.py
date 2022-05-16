
# "entry" and "exit" markers (fixed IDs) are ordered in time and may go in any position
_MARKER_ID_ENTRY = 43573010
_MARKER_ID_EXIT = 1539036744
# older versions (v62<=) use simpler IDs 0/1 for entry/exit, while other cues do use tids
_MARKER_ID_ENTRY_OLD = 0
_MARKER_ID_EXIT_OLD = 1

class _AkMarker(object):
    def __init__(self, node):
        self.id = None
        self.pos = None
        self.node = None
        self.npos = None
        self._build(node)

    def _build(self, node):
        self.node = node
        self.id = node.find(name='id').value()
        self.npos = node.find(name='fPosition')
        self.pos = self.npos.value()
        #pMarkerName: optional, found in later versions


class AkMarkerList(object):
    def __init__(self, node):
        self._markers = []
        self.fields = []
        self._build(node)

    def _build(self, node):
        nbase = node.find(name='pArrayMarkers')
        if not nbase:
            return
        
        nmarkers = nbase.finds(name='AkMusicMarkerWwise')
        for nmarker in nmarkers:
            marker = _AkMarker(nmarker)
            self._markers.append(marker)

    def _get_marker(self, ids, must_exist=False):
        for marker in self._markers:
            if marker.id in ids:
                return marker
        if must_exist:
            raise ValueError("can't find marker")
        return None

    def get_entry(self):
        return self._get_marker([_MARKER_ID_ENTRY, _MARKER_ID_ENTRY_OLD], must_exist=True)

    def get_exit(self):
        return self._get_marker([_MARKER_ID_EXIT, _MARKER_ID_EXIT_OLD], must_exist=True)
