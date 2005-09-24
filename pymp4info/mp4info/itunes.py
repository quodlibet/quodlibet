# An iTunes metadata reader
#
# Copyright 2005 Alexey Bobyakov <claymore.ws@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

# I used APE tag reader by Joe Wreschnig <piman@sacredchao.net>
# and id3 support for Mutagen by Michael Urman as an examples
# for this code. Basic code for reading atoms has been taken from
# libmetatag written by Pipian <pipian@pipian.com>.

# From mpeg4ip/lib/mp4v2/mp4meta.cpp:
# "The iTunes tagging seems to support any tag field name
# but there are some predefined fields, also known from the QuickTime
# format
#
# predefined fields (the ones I know of until now):
# - ©nam : Name of the song/movie (string)
# - ©ART : Name of the artist/performer (string)
# - ©wrt : Name of the writer (string)
# - ©alb : Name of the album (string)
# - ©day : Year (4 bytes, e.g. "2003") (string)
# - ©too : Tool(s) used to create the file (string)
# - ©cmt : Comment (string)
# - ©gen : Custom genre (string)
# - ©grp : Grouping (string)
# - trkn : Tracknumber (8 byte string)
#           16 bit: empty
#           16 bit: tracknumber
#           16 bit: total tracks on album
#           16 bit: empty
# - disk : Disknumber (8 byte string)
#           16 bit: empty
#           16 bit: disknumber
#           16 bit: total number of disks
#           16 bit: empty
# - gnre : Genre (16 bit genre) (ID3v1 index + 1)
# - cpil : Part of a compilation (1 byte, 1 or 0)
# - tmpo : Tempo in BPM (16 bit)
# - covr : Cover art (xx bytes binary data)
# - ---- : Free form metadata, can have any name and any data"

import os
from cStringIO import StringIO
from struct import pack, unpack

class error(IOError): pass
class FileNotFoundError(error, OSError): pass
class InvalidFormatError(error): pass
class AtomNotFoundError(error): pass

# iTunes atom types

COMMON, NUMERIC_WITH_PARTS, NUMERIC, COMPILATION, COVER, FREE_FORM_TEXT, FREE_FORM_BINARY = range(7)

class iTunesTag(object):
    CommonAtoms = ["\251nam", "\251ART", "\251wrt", "\251alb", "\251too",
                   "\251cmt", "\251gen", "\251grp", "covr", "\251day"]
    NumericAtoms = ["gnre", "tmpo"]
    NumericWithPartsAtoms = ["trkn", "disk"]
    KnownAtoms = CommonAtoms + NumericAtoms + NumericWithPartsAtoms + ["covr", "cpil"]
    
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError("%s does not exist" % filename)

        self.filename = filename
        self.__dict = {}
        self.__atoms = {}
        self.__old_meta_size = -1

        f = file(filename)
        tag, self.__old_meta_size = self.__find_tag(f)
        f.close()

        if tag: self.__parse_tag(tag)

    def __find_tag(self, f):
        atom_size = _read_int(f.read(4)) - 4
        buffer = f.read(8)
        if buffer[:4] != "ftyp":
            raise AtomNotFoundError("Atom 'ftyp' is not found")
        
        f.seek(-8, 1)
        f.read(atom_size)
        while True:
            buffer = f.read(4)
            if not buffer:
                raise AtomNotFoundError("Atom 'moov' is not found")
            atom_size = _read_int(buffer) - 4
            pos = f.tell()
            buffer = f.read(4)
            if buffer[:4] == "moov":
                buffer += f.read(atom_size - 4)
                break
            f.seek(atom_size - 4, 1)

        if buffer[:4] != "moov":
            raise AtomNotFoundError("Atom 'moov' is not found")
        
        self.__atoms["moov"] = pos - 4
        parent_size = atom_size
        bp = 4
        while bp < parent_size:
            atom_size = _read_int(buffer[bp:bp+4]) - 4
            bp += 4
            if buffer[bp:bp + 4] == "udta":
                break
            bp += atom_size

        if buffer[bp:bp+4] != "udta":
            raise AtomNotFoundError("Atom 'moov.udta' is not found")

        self.__atoms["udta"] = self.__atoms["moov"] + bp
        parent_size = atom_size
        start_pos = bp
        bp += 4
        while bp - start_pos < parent_size:
            atom_size = _read_int(buffer[bp:bp + 4]) - 4
            bp += 4
            if buffer[bp:bp + 4] == "meta":
                break
            bp += atom_size

        if buffer[bp:bp+4] != "meta":
            return None, 0
    
        self.__atoms["meta"] = self.__atoms["moov"] + bp
        meta_size = atom_size + 4
        parent_size = atom_size
        start_pos = bp
        bp += 8
        while bp - start_pos < parent_size:
            atom_size = _read_int(buffer[bp:bp + 4]) - 4
            bp += 4
            if buffer[bp:bp + 4] == "ilst":
                break
            bp += atom_size

        if buffer[bp:bp+4] != "ilst":
            return None, 0

        bp -= 8
        return buffer[bp:], meta_size

    def __parse_tag(self, tag):
        f = StringIO(tag)
        size = unpack(">Q", f.read(8))[0] - 4
        buffer = f.read(size)
        bp = 4
        while bp < len(buffer):
            atom_size = _read_int(buffer[bp:bp+4])
            key = buffer[bp+4:bp+8]
            spec = iTunesSpec(key)
            if spec:
                value, name = spec.read(buffer[bp+8:bp+atom_size])
                if name: self[name] = value
                else: self[key] = value
            bp += atom_size

    def __generate_meta(self):
        """Generates 'meta' atom from the tags"""
        ilst = ""
        for k, v in self:
            ilst += v.write(k)
        ilst_size = len(ilst) + 8
        hdlr = pack(">i12s13s", 33, "hdlr", "mdirappl")
        meta_size = ilst_size + len(hdlr) + 16
        meta = pack(">i8s", meta_size, "meta") + hdlr + pack(">Q4s", ilst_size, "ilst") + ilst
        return meta
    
    def write(self):
        """This function writes any changes you've made."""
        if len(self.__dict):
            self.__sanitize()
            meta = self.__generate_meta()
            offset = len(meta) - self.__old_meta_size
            f = file(self.filename, "rb+")
            f.seek(self.__atoms["moov"], 0)
            size = _read_int(f.read(4))
            new_size = pack(">I", size + offset)
            f.seek(-4, 1)
            f.write(new_size)
            f.seek(self.__atoms["udta"] - self.__atoms["moov"] - 4, 1)
            size = _read_int(f.read(4))
            new_size = pack(">I", size + offset)
            f.seek(-4, 1)
            f.write(new_size)
            pos = f.tell()
            # Change meta
            if len(self.__atoms) == 3: 
                f.seek(self.__atoms["meta"] + self.__old_meta_size)
                leftover = f.read()
                f.seek(pos)
                f.seek(self.__atoms["meta"] - self.__atoms["udta"] - 4, 1)
            # Create meta
            else: 
                f.seek(4, 1)
                leftover = f.read()
                f.seek(pos + 4)
            f.truncate()
            f.write(meta + leftover)
            f.flush()
            f.seek(0, 0)
            f.close()
        # We've deleted all tags so we delete 'meta' atom
        elif self.__old_meta_size > 0:
            offset = -self.__old_meta_size
            f = file(self.filename, "rb+")
            f.seek(self.__atoms["moov"], 0)
            size = _read_int(f.read(4))
            new_size = pack(">I", size + offset)
            f.seek(-4, 1)
            f.write(new_size)
            f.seek(self.__atoms["udta"] - self.__atoms["moov"] - 4, 1)
            size = _read_int(f.read(4))
            new_size = pack(">I", size + offset)
            f.seek(-4, 1)
            f.write(new_size)
            pos = f.tell()
            f.seek(self.__atoms["meta"] + self.__old_meta_size)
            leftover = f.read()
            f.seek(pos)
            f.seek(self.__atoms["meta"] - self.__atoms["udta"] - 4, 1)
            f.truncate()
            f.write(leftover)
            f.flush()
            f.seek(0, 0)
            f.close()
        return

    def __iter__(self): return self.__dict.iteritems()
    def keys(self): return self.__dict.keys()
    def values(self): return self.__dict.values()
    def items(self): return self.__dict.items()

    def __contains__(self, k): return self.__dict.__contains__(k)
    def __getitem__(self, k): return self.__dict[k]
    def __delitem__(self, k): del(self.__dict[k])
    def __setitem__(self, k, v):
        """This functions tries to guess at what type of atom you want
        store. If you pass in a valid UTF-8 or Unicode string, it treats
        it as a text value. If you pass in a list, it treats it as a
        list of string/Unicode values. If you pass in a string that is
        not valid UTF-8, it assumes it is a binary value."""
        if k in self.CommonAtoms: atom = COMMON
        elif k in self.NumericWithPartsAtoms: atom = NUMERIC_WITH_PARTS
        elif k in self.NumericAtoms: atom = NUMERIC
        elif k == "cpil": atom = COMPILATION
        elif k == "covr": atom = COVER
        else: atom = FREE_FORM_TEXT
        if isinstance(v, unicode):
            # unicode? we've got to be text.
            v = iTunesAtom(_utf8(v), atom)
        elif isinstance(v, list):
            # list? text.
            v = iTunesAtom("\0".join(map(_utf8, v)), atom)
        else:
            if k in self.KnownAtoms:
                v = iTunesAtom(v, atom)
            else:
                try: dummy = v.decode("utf-8")
                except UnicodeError:
                    # invalid UTF8 text, probably binary
                    v = iTunesAtom(v, FREE_FORM_BINARY)
                else:
                    # valid UTF8, probably text
                    v = iTunesAtom(v, FREE_FORM_TEXT)
        self.__dict[k] = v

    def genre_to_string(self, v):
        from _constants import GENRES
        try:
            genre = GENRES[int(v)-1]
            return genre
        except KeyError:
            return v
    
    def __sanitize(self):
        """Custom tags should be saved in "\251gen" and
        ID3v1 ones in "gnre"."""
        from _constants import GENRES
        if "gnre" in self and self["gnre"] not in GENRES:
            self["\251gen"] = self["gnre"]
            del self["gnre"]
        if "\251gen" in self and self["\251gen"] in GENRES:
            self["gnre"] = GENRES.index(str(self["\251gen"])) + 1
            del self["\251gen"]

def iTunesAtom(value, kind):
    if kind == COMMON: return iTunesCommonAtom(value, kind)
    elif kind == NUMERIC_WITH_PARTS: return iTunesNumericWithPartsAtom(value, kind)
    elif kind == NUMERIC: return iTunesNumericAtom(value, kind)
    elif kind == COMPILATION: return iTunesCompilationAtom(value, kind)
    elif kind == COVER: return iTunesCoverArtAtom(value, kind)
    elif kind == FREE_FORM_TEXT: return iTunesFreeFormTextAtom(value, kind)
    elif kind == FREE_FORM_BINARY: return iTunesFreeFormBinaryAtom(value, kind)
    else: raise ValueError("kind must be COMMON, NUMERIC_WITH_PARTS, NUMERIC,\n" +
                           "COMPILATION, COVER, FREE_FORM_TEXT or FREE_FORM_BINARY")

def iTunesSpec(key):
    if key in iTunesTag.CommonAtoms or key == "covr": return CommonSpec()
    elif key in iTunesTag.NumericWithPartsAtoms: return NumericWithPartsSpec()
    elif key in iTunesTag.NumericAtoms: return NumericSpec()
    elif key == "cpil": return ByteSpec()
    elif key == "----": return FreeFormSpec()
    else: return None

class CommonSpec(object):
    # 4B: atom size
    # 4B: atom name
    # 4B: data property size
    # 4B: "data"
    # 4B: 1
    # 4B: 0
    # value
    def write(self, key, data):
        if key == "\251day":
            data = data[:4]
        size = len(data) + 16
        return pack(">I4sI4s2I", size + 8, key, size, "data", 1, 0) + data
    
    def read(self, data):
        value_size = _read_int(data[0:4])
        value = data[16:value_size]
        return value, ''

class NumericWithPartsSpec(object):
    # 4B: atom size
    # 4B: atom name
    # 4B: data property size
    # 4B: "data"
    # 4B: 0
    # 4B: 0
    # 2B: 0
    # 2B: number
    # 2B: total
    # 2B: 0
    def write(self, key, data):
        if '/' in data:
            ind = data.index('/') + 1
            num = int(data[:ind-1])
            tot = int(data[ind:])
        else:
            tot = 0
            num = int(data)
        return pack(">I4sI4s2I4H", 32, key, 24, "data", 0, 0, 0, num, tot, 0)
    
    def read(self, data):
        num = _read_short(data[18:20])
        tot = _read_short(data[20:22])
        value = str(num)
        if tot:
            value += "/" + str(tot)
        return value, ''

class NumericSpec(object):
    # 4B: atom size
    # 4B: atom name
    # 4B: data property size
    # 4B: "data"
    # 4B: 0
    # 4B: 0
    # 2B: value
    def write(self, key, data):
        return pack(">I4sI4s2IH", 26, key, 18, "data", 0, 0, int(data))
    
    def read(self, data):
        return str(_read_short(data[16:18])), ''

class ByteSpec(object):
    # 4B: atom size
    # 4B: atom name
    # 4B: data property size
    # 4B: "data"
    # 4B: 0
    # 4B: 0
    # 1B: value
    def write(self, key, data):
        if data == '0' or data == 'n':
            return pack(">I4sI4s2IB", 25, key, 17, "data", 0, 0, 0)
        else: return pack(">I4sI4s2IB", 25, key, 17, "data", 0, 0, 1)
    
    def read(self, data):
        return _read_char(data[16]), ''

class FreeFormSpec(object):
    # 4B: atom size
    # 4B: atom name
    # 4B: mean property size
    # 4B: "mean"
    # 4B: 0
    # mean
    # 4B: name property size
    # 4B: "name"
    # 4B: 0
    # name
    # 4B: data property size
    # 4B: "data"
    # 4B: 1
    # 4B: 1
    # value
    def write(self, name, data):
        name = _utf8(name)
        name_size = len(name)
        value_size = len(data) + 16
        mean = "com.apple.iTunes"
        size = name_size + value_size + 48
        return pack(">I4sI4sI16sI4sI" + str(name_size) + "sI4sII",
                    size, "----", 28, "mean", 0, mean,
                    name_size + 12, "name", 0, name,
                    value_size, "data", 1, 1) + data

    def read(self, data):
        bp = 28
        name_size = _read_int(data[bp:bp+4]) - 12
        bp += 12
        name = data[bp:bp+name_size]
        bp += name_size
        value_size = _read_int(data[bp:bp+4]) - 16
        bp += 16
        value = data[bp:bp+value_size]
        return value, name

class _iTunesAtom(object):
    def __init__(self, value, kind):
        self.kind = kind
        self.value = value

    def __len__(self): return len(self.value)
    def __str__(self): return self.value

class _iTunesStringAtom(_iTunesAtom):

    def __unicode__(self):
        return unicode(str(self), "utf-8")
    
    def __iter__(self):
        return iter(unicode(self).split("\0"))
    
    def __getitem__(self, i):
        return unicode(self).split("\0")[i]

    def __len__(self): return self.value.count("\0") + 1

    def __cmp__(self, other):
        return cmp(unicode(self), other)
    
    def __setitem__(self, i, v):
        l = list(self)
        l[i] = v.encode("utf-8")
        self.value = "\0".join(l).encode("utf-8")

class iTunesCommonAtom(_iTunesStringAtom):
    __spec = CommonSpec()
    
    def write(self, key):
        return self.__spec.write(key, self.value)
    
    def __repr__(self):
        return "<iTunesCommonAtom %r>" % list(self.value)

class iTunesCoverArtAtom(_iTunesStringAtom):
    __spec = CommonSpec()

    def write(self, key):
        return self.__spec.write(key, self.value)
    
    def __repr__(self):
        return "<iTunesCoverArtAtom (%d bytes)>" % len(self)

class iTunesNumericWithPartsAtom(_iTunesStringAtom):
    __spec = NumericWithPartsSpec()

    def write(self, key):
        return self.__spec.write(key, self.value)
        
    def __repr__(self):
        return "<iTunesNumericWithPartsAtom %r>" % list(self.value)

class iTunesNumericAtom(_iTunesStringAtom):
    __spec = NumericSpec()

    def write(self, key):
        return self.__spec.write(key, self.value)

    def __repr__(self):
        return "<iTunesNumericAtom %r>" % list(self.value)

class iTunesCompilationAtom(_iTunesStringAtom):
    __spec = ByteSpec()
    
    def __str__(self):
        return str(self.value)
    
    def write(self, key):
        return self.__spec.write(key, self.value)
    
    def __repr__(self):
        return "<iTunesCompilationAtom %r>" % list(self.value)

class iTunesFreeFormTextAtom(_iTunesStringAtom):
    __spec = FreeFormSpec()

    def write(self, key):
        return self.__spec.write(key, self.value)
    
    def __repr__(self):
        return "<iTunesFreeFormTextAtom %r>" % list(self.value)

class iTunesFreeFormBinaryAtom(_iTunesAtom):
    __spec = FreeFormSpec()
    
    def write(self, key):
        return self.__spec.write(key, self.value)
    
    def __repr__(self):
        return "<iTunesFreeFormBinaryAtom (%d bytes)>" % len(self)

def _read_int(data): return unpack('>I', data)[0]
def _read_short(data): return unpack('>H', data)[0]
def _read_char(data): return unpack('>B', data)[0]

def _utf8(data):
    if isinstance(data, str):
        return data.decode("utf-8", "replace").encode("utf-8")
    elif isinstance(data, unicode):
        return data.encode("utf-8")
    else: raise TypeError("only unicode/str types can be converted to UTF-8")
