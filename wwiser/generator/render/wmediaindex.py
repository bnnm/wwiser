import logging


# preloaded list of internal/memory .wem in bnk, as txtp will need to find them

class MediaIndex(object):
    def __init__(self):
        self._media_banks = {}              # bank + sid > internal wem index
        self._media_sids = {}               # sid > bank + internal wem index
        self._missing_media = {}            # media (wem) objects missing in some bank
        self._event_based_packaging = False

    def set_event_based_packaging(self, flag):
        self._event_based_packaging = flag

    def get_missing_media(self):
        return self._missing_media

    def get_event_based_packaging(self):
        return self._event_based_packaging

    #--------------------------------------------------------------------------

    def load(self, nchunk):
        # load another chunk (may be N)
        chunkname = nchunk.get_name()
        if chunkname != 'MediaIndex':
            return

        # preload indexes for internal wems
        bankname = nchunk.get_root().get_filename()
        nsids = nchunk.finds(type='sid')
        for nsid in nsids:
            sid = nsid.value()
            attrs = nsid.get_parent().get_attrs()
            index = attrs.get('index')
            if index is not None:
                self._add_media_index(bankname, sid, index)
        return

    # A game could load bgm.bnk + media1.bnk, and bgm.bnk point to sid=123 in media1.bnk.
    # But if user loads bgm1.bnk + media1.bnk + media2.bnk both media banks may contain sid=123,
    # so media_banks is used to find the index inside a certain bank (sid repeats allowed) first,
    # while media_sids is used to find any bank+index that contains that sid (repeats ignored).
    def _add_media_index(self, bankname, sid, index):
        self._media_banks[(bankname, sid)] = index
        if sid not in self._media_sids:
            self._media_sids[sid] = (bankname, index)

    def get_media_index(self, bankname, sid):
        #seen 0 in v112 test banks
        if not sid:
            return None

        # try in current bank
        index = self._media_banks.get((bankname, sid))
        if index is not None:
            return (bankname, index)

        # try any bank
        media = self._media_sids.get(sid)
        if media is not None:
            return media

        logging.debug("generator: missing memory wem %s", sid)
        self._missing_media[sid] = True
        return None
