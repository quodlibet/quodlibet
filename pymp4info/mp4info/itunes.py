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

import os, mp4, sre
from cStringIO import StringIO
from struct import pack, unpack

class error(IOError): pass
class FileNotFoundError(error, OSError): pass
class InvalidFormatError(error): pass
class AtomNotFoundError(error): pass

TEXT, BINARY = range(2)

class iTunesTag(object):
    CommonAtoms = ["\251nam", "\251ART", "\251wrt", "\251alb",
                   "\251too", "\251gen", "\251grp", "\251day", "\251cmt", "\251lyr"]
    NumericAtoms = ["gnre", "tmpo"]
    NumericWithPartsAtoms = ["trkn", "disk"]
    KnownAtoms = CommonAtoms + NumericAtoms + NumericWithPartsAtoms + ["covr", "cpil"]
    
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError("%s does not exist" % filename)

        self.filename = filename
        self.__dict = {}

        f = file(filename)
        tag = self.__find_tag(f)
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
    
        meta_size = atom_size + 4
        parent_size = atom_size
        start_pos = bp
        bp += 8
        ilst_pos = -1
        while bp - start_pos < parent_size:
            atom_size = _read_int(buffer[bp:bp + 4]) - 4
            bp += 4
            if buffer[bp:bp + 4] == "ilst":
                ilst_pos = bp
                break
            bp += atom_size

        if ilst_pos == -1:
            return None, 0
        
        bp = ilst_pos - 4
        return buffer[bp:]

    def __parse_tag(self, tag):
        f = StringIO(tag)
        size = unpack(">I", f.read(4))[0] - 4
        buffer = f.read(size)
        bp = 4
        while bp < len(buffer):
            atom_size = _read_int(buffer[bp:bp+4])
            key = buffer[bp+4:bp+8]
            spec = iTunesSpec(key)
            if spec:
                value, name = spec.read(buffer[bp+8:bp+atom_size])
                if name: self[name] = str(value)
                else: self[key] = str(value)
            bp += atom_size
	
    def __iter__(self): return self.__dict.iteritems()
    def keys(self): return self.__dict.keys()
    def values(self): return self.__dict.values()
    def items(self): return self.__dict.items()

    def __contains__(self, k): return self.__dict.__contains__(k)
    def __getitem__(self, k): return self.__dict[k]
    def __delitem__(self, k): del(self.__dict[k])
    def __setitem__(self, k, v):
        if not isinstance(v, _iTunesValue):
            if k == "\251lyr": sep = "\r"
            elif (k in ["\251cmt", "\251too"] or
                 k not in self.KnownAtoms):
                sep = "\r\n"
            else: sep = ", "
            if isinstance(v, unicode):
                # unicode? we've got to be text.
                v = iTunesValue(_utf8(v), TEXT, sep)
            elif isinstance(v, list):
                # list? text.
                v = iTunesValue(sep.join(map(_utf8, v)), TEXT, sep)
            else:
                try: dummy = v.decode("utf-8")
                except UnicodeError:
                   # invalid UTF8 text, probably binary
                   v = iTunesValue(v, BINARY)
                else:
                   # valid UTF8, probably text
                   v = iTunesValue(v, TEXT, sep)
        self.__dict[k] = v
	
    def write(self, filename = None):
        """Saves any changes you've made to the file, or to a different
        file if you specify one. Any existing tag will be removed."""
        filename = filename or self.filename
        self.__sanitize()
        f = mp4.MP4File(filename)
        f.deleteAllTags()
        for k, v in self:
            f.setTag(k, str(v))
            
    def __sanitize(self):
        numeric = sre.compile("^\d+(/\d+)?$")
        date = sre.compile("^\d{1,4}$")
        for key in ["trkn", "disk"]:
            if key in self and not numeric.match(str(self[key])):
                if key == "trkn": new_key = "tracknumber"
                else: new_key = "discnumber"
                self[new_key] = self[key]
                del(self[key])
        for key in ["tracknumber", "discnumber"]:
            if key in self and numeric.match(str(self[key])):
                if key == "tracknumber": new_key = "trkn"
                else: new_key = "disk"
                self[new_key] = self[key]
                del(self[key])
        tempo = sre.compile("^\d+$")
        if "tmpo" in self and not date.match(str(self["tmpo"])):
            self["bpm"] = self["tmpo"]
            del(self["tmpo"])
        if "cpil" in self:
            if self["cpil"][0] == '1' or self["cpil"][0] == 'y':
                self["cpil"] = '1'
            else: self["cpil"] = '0'

def iTunesSpec(key):
    if key in iTunesTag.CommonAtoms + ["covr"]: return CommonSpec()
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
    def read(self, data):
        num = _read_short(data[18:20])
        tot = _read_short(data[20:22])
        value = str(num).zfill(2)
        if tot:
            value += "/" + str(tot).zfill(2)
        return value, ''

class NumericSpec(object):
    # 4B: atom size
    # 4B: atom name
    # 4B: data property size
    # 4B: "data"
    # 4B: 0
    # 4B: 0
    # 2B: value
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
    
def iTunesValue(value, kind, sep = ""):
    """It is not recommended you construct iTunes values manually; instead
    use iTunesTag's __setitem__."""
    if kind == TEXT: return iTunesTextValue(value, kind, sep)
    elif kind == BINARY: return iTunesBinaryValue(value, kind)
    else: raise ValueError("kind must be TEXT or BINARY")

class _iTunesValue(object):
    def __init__(self, value, kind):
        self.kind = kind
        self.value = value

    def __len__(self): return len(self.value)
    def __str__(self): return self.value

class iTunesTextValue(_iTunesValue):
    def __init__(self, value, kind, sep):
        self.kind = kind
        self.value = value
        self.separator = sep
    
    def __unicode__(self):
        return unicode(str(self), "utf-8")

    def __iter__(self):
        return iter(unicode(self).split(self.separator))

    def __getitem__(self, i):
        return unicode(self).split(self.separator)[i]

    def __len__(self): return self.value.count(self.separator) + 1

    def __cmp__(self, other):
        return cmp(unicode(self), other)

    def __setitem__(self, i, v):
        l = list(self)
        l[i] = v.encode("utf-8")
        self.value = self.separator.join(l).encode("utf-8")

    def __repr__(self):
        return "<iTunesTextValue %r>" % list(self)

class iTunesBinaryValue(_iTunesValue):
    """Binary values may be converted to a string of bytes. They are
    used for anything not intended to be human-readable."""
    def __repr__(self):
        return "<iTunesBinaryValue (%d bytes)>" % len(self)

def _read_int(data): return unpack('>I', data)[0]
def _read_short(data): return unpack('>H', data)[0]
def _read_char(data): return unpack('>B', data)[0]

def _utf8(data):
    if isinstance(data, str):
        return data.decode("utf-8", "replace").encode("utf-8")
    elif isinstance(data, unicode):
        return data.encode("utf-8")
    else: raise TypeError("only unicode/str types can be converted to UTF-8")
