

class AkFxChunk(object):
    def __init__(self, nfx):
        self.index = None
        self.nid = None
        self.is_inline = False
        self.is_shareset = False
        self.is_rendered = False
        self.bfx = None
        self._build(nfx)

    def _build(self, nfx):
        nindex = nfx.find(name='uFXIndex') #not in older versions
        nid = nfx.find(name='fxID') #plugin ID in older versions
        nshareset = nfx.find(name='bIsShareSet') #not in older versions (inline plugins)
        nrendered = nfx.find(name='bIsRendered') #_bIsRendered in bus, never set

        if nindex:
            self.index = nindex.value()
        self.is_inline = nshareset is None

        if not self.is_inline:
            self.nid = nid
            self.is_shareset = nshareset.value()

        if nrendered:
            self.is_rendered = nrendered.value()
        #TODO load inline


class AkFxChunkList(object):
    def __init__(self, node, builder):
        self.init = False
        self._fxcs = [] #exact max is 4
        self._flags = 0
        self._build(node, builder)

    def _build(self, node, builder):
        if not node:
            return

        nfxchunk = node.find(name='pFXChunk')
        if not nfxchunk:
            return

        # current list overwrites parent, even if empty
        self.init = True

        # & 0x1/0x2/0x4/0x8 = bypass index 0/1/2/3, 0x10 = bypass all
        flags = node.find1(name='bitsFXBypass')
        if flags is not None:
            self._flags = flags.value()
        else:
            flags = node.find1(name='bBypassAll')
            if flags and flags.value():
                self._flags = 0x10

        nfxs = nfxchunk.finds(name='FXChunk')
        for nfx in nfxs:            
            fxc = AkFxChunk(nfx)
            if fxc.is_rendered: #baked in
                continue

            if fxc.is_shareset:
                bfx = builder._get_bnode_link_shareset(fxc.nid)
            else: #AkFxCustom, regular audio node
                bfx = builder._get_bnode_link(fxc.nid)

            if not bfx:
                continue

            fxc.bfx = bfx
            if fxc.index is None:
                self._fxcs.append(fxc)
            else:
                if not self._fxcs:
                    self._fxcs = [None] * 4
                self._fxcs[fxc.index] = fxc

    def get_gain(self):
        #TODO: read flags
        gain = 0
        for fxc in self._fxcs:
            if not fxc:
                continue
            gain += fxc.bfx.fx.gain
        return gain
