
class AkAuxList(object):
    def __init__(self, node, bparent, hircs):
        self.init = False
        self._auxs = [] #exact max is 4
        self._build(node, bparent, hircs)

    def _build(self, node, bparent, hircs):
        if not node:
            return

        # flag is implicit and always set, but just in case
        nhas = node.find1(name='bHasAux')
        if not nhas or nhas.value() <= 0:
            return

        # object may have defined auxs, but not override them = not used, however flag is only set in childs
        nover = node.find1(name='bOverrideUserAuxSends')
        if not nover or bparent and nover.value() <= 0:
            return

        # current list overwrites parent, even if empty
        self.init = True

        # always 4 entries, ID 0 if not used
        nauxids = node.finds(name='auxID') #should exist
        for nauxid in nauxids:
            baux = hircs._read_bus(nauxid) #parent bus of this bus
            if not baux:
                continue
            self._auxs.append(baux)

    def get_bauxs(self):
        return self._auxs
