# An APEv2 tag reader
#
# Copyright 2004 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

# Based off the documentation found at
# http://www.personal.uni-jena.de/~pfk/mpp/sv8/apetag.html
# (Available at http://web.archive.org/web/20040205023703/http://www.personal.uni-jena.de/~pfk/mpp/sv8/apetag.html)

import struct
from cStringIO import StringIO

# There are three different kinds of APE tag values.
TEXT, BINARY, EXTERNAL = range(3)

def _debug(str): print str
def _dummy(str): pass
debug = _debug

class error(IOError): pass
class InvalidTagError(error): pass

class APETag(object):
    def __init__(self, filename):
        self.filename = filename
        debug("loading %s" % self.filename)
        f = file(filename)

        self.tag_offset(f)
        debug("tag offset: 0x%x" % self.offset)
        f.seek(self.offset)

        f.read(8) # "APETAGEX"

        # 4 byte version
        version = _read_int(f)
        debug("tag version: %d" % version)
        if version < 2000 or version >= 3000:
            raise InvalidTagError(
                "module only supports APEv2 (2000-2999), found %d" % version)

        # 4 byte tag size
        tag_size = _read_int(f)
        debug("tag size: %d" % tag_size)

        # 4 byte item count
        item_count = _read_int(f)
        debug("item count: %d" % item_count)

        # 4 byte flags
        self.flags = _read_int(f)
        debug("flags: 0x%x" % self.flags)
        if self.flags & (1 << 29) == 0:
            raise InvalidTagError("found footer, not header")

        # 8 bytes reserved
        f.read(8)

        tag_data = f.read(tag_size)
        if len(tag_data) < tag_size:
            debug("W: tag size does not match file size")
        f.close()

        self.dict = {}

        f = StringIO(tag_data)
        for i in range(item_count):
            size = _read_int(f)
            flags = _read_int(f)
            debug("size: %d, flags 0x%x" % (size, flags))

            kind = (flags & 6) >> 1
            key = ""
            while key[-1:] != '\0': key += f.read(1)
            key = key[:-1]
            value = f.read(size)
            self.dict[APEKey(key)] = APEValue(kind, value)
            debug("key %s, value %r" % (key, value))

    def tag_offset(self, f):
        # APEv2 tags should be less than 8KB and at the end of the file.
        # In the interest of my sanity this only reads tags at the end.

        # TODO:
        # * Check existing offset if available
        # * Check for footerness, rewind to right point
        # * If all else fails scan the whole file
        f.seek(0, 2)
        size = min(10240, f.tell())
        f.seek(-size, 2)
        data = f.read(size)

        # store offset to the start of the tag
        try: index = data.index("APETAGEX")
        except ValueError: raise InvalidTagError("no tag header found")
        else: self.offset = (f.tell() - size) + index

    def __iter__(self):
        return self.dict.iteritems()

    def __getitem__(self, k): return self.dict[k]
    def __setitem__(self, k, v): self.dict[k] = v

class APEKey(str):
    """An APE key is an ASCII string of length 2 to 255. The specification's
    case rules are nonsense, so this object is case-preserving but not
    case-sensitive, i.e. "album" == "Album"."""


    def __cmp__(self, o):
        return cmp(self.lower(), o.lower())
    
    def __eq__(self, o):
        return self.lower() == o.lower()
    
    def __hash__(self):
        return str.__hash__(self.lower())

    def __repr__(self): return "<APEKey %s>" % str.__repr__(self)

def APEValue(kind, value):
    if kind == TEXT: return APETextValue(kind, value)
    elif kind == BINARY: return APEBinaryValue(kind, value)
    elif kind == EXTERNAL: return APEExtValue(kind, value)
    else: raise ValueError("kind must be TEXT, BINARY, or EXTERNAL")

class _APEValue(object):
    def __init__(self, kind, value):
        self.kind = kind
        self.value = value

    def __len__(self): return len(self.value)
    def __str__(self): return self.value

class APETextValue(_APEValue):
    def __unicode__(self):
        return unicode(str(self), "utf-8")

    def __iter__(self):
        return iter(unicode(self).split("\0"))

    def __getitem__(self, i):
        return unicode(self).split("\0")[i]

    def __setitem__(self, i, v):
        list = list(self)
        list[i] = v.encode("utf-8")
        self.value = "\0".join(list).encode("utf-8")

    def __repr__(self):
        return "<APETextValue %r>" % list(self)

class APEBinaryValue(_APEValue):
    def __repr__(self):
        return "<APEBinaryValue (%d bytes)>" % len(self)

class APEExtValue(_APEValue):
    def __repr__(self):
        return "<APEExtValue ref=%s>" % len(self.value)

def _read_int(f):
    # ints in APE are LE
    return struct.unpack('<i', f.read(4))[0]
