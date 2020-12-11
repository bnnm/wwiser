import re

class Fnv(object):
    FNV_DICT = '0123456789abcdefghijklmnopqrstuvwxyz_'
    FNV_FORMAT = re.compile(r"^[a-z_][a-z0-9\_]*$")
    FNV_FORMAT_EX = re.compile(r"^[a-z_0-9][a-z0-9_()\- ]*$")

    def is_hashable(self, lowname):
        return self.FNV_FORMAT.match(lowname)

    def is_hashable_extended(self, lowname):
        return self.FNV_FORMAT_EX.match(lowname)


    # Find actual name from a close name (same up to last char) using some fuzzy searching
    # ('bgm0' and 'bgm9' IDs only differ in the last byte, so it calcs 'bgm' + '0', '1'...)
    def unfuzzy_hashname_lw(self, id, lowname, hashname):
        if not id or not hashname:
            return None

        namebytes = bytearray(lowname, 'UTF-8')
        basehash = self._get_hash(namebytes[:-1]) #up to last byte
        for c in self.FNV_DICT: #try each last char
            id_hash = self._get_partial_hash(basehash, ord(c))

            if id_hash == id:
                c = c.upper()
                for cs in hashname: #upper only if all base name is all upper
                    if cs.islower():
                       c = c.lower()
                       break

                hashname = hashname[:-1] + c
                return hashname
        # it's possible to reach here with incorrect (manually input) ids,
        # since not all 255 values are in FNV_DICT
        return None

    def unfuzzy_hashname(self, id, hashname):
        return self.unfuzzy_hashname_lw(id, hashname.lower(), hashname)

    # Partial hashing for unfuzzy'ing.
    def _get_partial_hash(self, hash, value):
        hash = hash * 16777619 #FNV prime
        hash = hash ^ value #FNV xor
        hash = hash & 0xFFFFFFFF #python clamp
        return hash

    # Standard AK FNV-1 with 32-bit.
    def _get_hash(self, namebytes):
        hash = 2166136261 #FNV offset basis

        for namebyte in namebytes:  #for i in range(len(namebytes)):
            hash = hash * 16777619 #FNV prime
            hash = hash ^ namebyte #FNV xor
            hash = hash & 0xFFFFFFFF #python clamp
        return hash

    def get_hash(self, name):
        return self.get_hash_lw(name.lower())

    def get_hash_lw(self, lowname):
        namebytes = bytes(lowname, 'UTF-8')
        return self._get_hash(namebytes)
