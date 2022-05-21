import logging


# default Wwise config in init.bnk

class GlobalSettings(object):
    def __init__(self):
        self._rtpc_default = {}

    #--------------------------------------------------------------------------

    def load(self, nchunk):
        # load another chunk (may be N)
        chunkname = nchunk.get_name()
        if chunkname != 'GlobalSettingsChunk':
            return

        for nitem in nchunk.get_children():
            itemname = nitem.get_name()

            # StateGroups: list of states (not always found)

            # pItems > SwitchGroups: same

            if itemname == 'pRTPCMgr': #RTPC info
                nrtpcrampings = nitem.finds(name='RTPCRamping')
                if not nrtpcrampings:
                    continue

                for nrtpcramping in nrtpcrampings:
                    nid = nrtpcramping.find1(name='RTPC_ID')
                    nvalue = nrtpcramping.find1(name='fValue')
                    if nid and nvalue:
                        id = nid.value()
                        value = nvalue.value()
                        self._rtpc_default[id] = value
                continue

            #acousticTextures: texture modifiers for game
        return

    def get_rtpc_default(self, id):
        return self._rtpc_default.get(id)
