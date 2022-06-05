

class AkFxChunk(object):
    def __init__(self, nfx):
        self.index = None
        self.nid = None
        self.is_shareset = False
        self.is_rendered = False
        self.bfx = None
        self._build(nfx)

    def _build(self, nfx):
        self.index = nfx.find(name='uFXIndex').value()
        self.nid = nfx.find(name='fxID')
        self.is_shareset = nfx.find(name='bIsShareSet').value()

        nrendered = nfx.find(name='bIsRendered') #_bIsRendered in bus, never set
        if nrendered:
            self.is_rendered = nrendered.value()


class AkFxChunkList(object):
    def __init__(self, node, builder):
        self.init = False
        self._fxcs = [None] * 4 #exact max
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
        self._flags = node.find(name='bitsFXBypass')

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
            self._fxcs[fxc.index] = fxc

    def get_gain(self):
        #TODO: read flags
        gain = 0
        for fxc in self._fxcs:
            if not fxc:
                continue
            gain += fxc.bfx.fx.gain
        return gain
