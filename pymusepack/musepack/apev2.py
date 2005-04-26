# An APEv2 tag reader
#
# Copyright 2005 Joe Wreschnig <piman@sacredchao.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# $Id$

# Based off the documentation found at
# http://www.personal.uni-jena.de/~pfk/mpp/sv8/apetag.html
# (Available at http://web.archive.org/web/20040205023703/http://www.personal.uni-jena.de/~pfk/mpp/sv8/apetag.html)

import os, struct
from cStringIO import StringIO

# There are three different kinds of APE tag values.
TEXT, BINARY, EXTERNAL = range(3)

HAS_HEADER = 1 << 31L
HAS_FOOTER = 1 << 30
IS_HEADER  = 1 << 29

def _debug(str): print str
def _dummy(str): pass
debug = _dummy

class error(IOError): pass
class FileNotFoundError(error, OSError): pass
class InvalidFormatError(error): pass

class APETag(object):
    """An APETag contains the tags in the file. It behaves much like a
    dictionary of key/value pairs, except that the keys must be strings,
    and the values a support APE tag value."""
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise FileNotFoundError("%s does not exist" % filename)
        elif os.path.getsize(filename) < 32:
            raise InvalidTagError("%s does not contain an APE tag" % filename)
        self.filename = filename
        self.__dict = {}

        f = file(filename)
        tag, count = self._find_tag(f)
        f.close()

        if tag: self._parse_tag(tag, count)

    def _parse_tag(self, tag, count):
        f = StringIO(tag)

        for i in range(count):
            size = _read_int(f.read(4))
            flags = _read_int(f.read(4))
            debug("size: %d, flags %#x" % (size, flags))

            # 1 and 2 bits are flags, 0-3
            kind = (flags & 6) >> 1
            if kind == 3:
                raise InvalidTagFormat("value type must be 0, 1, or 2")
            key = ""
            while key[-1:] != '\0': key += f.read(1)
            key = key[:-1]
            value = f.read(size)
            self.__dict[APEKey(key)] = APEValue(value, kind)
            debug("key %s, value %r" % (key, value))

    def _tag_start(self, f):
        try: f.seek(-32, 2)
        except IOError: f.seek(0, 0)
        if f.read(8) == "APETAGEX":
            f.read(4) # version
            tag_size = _read_int(f.read(4))
            f.seek(-(tag_size + 8), 2) # start of header
            return f.tell()
        else:
            f.seek(0, 2)
            return f.tell()

    def _find_tag(self, f):
        try: f.seek(-32, 2)
        except IOError: return None, 0
        data = f.read(32)
        if data.startswith("APETAGEX"):
            # 4 byte version
            version = _read_int(data[8:12])
            debug("tag version: %d" % version)
            if version < 2000 or version >= 3000:
                raise InvalidTagError(
                    "module only supports APEv2 (2000-2999), has %d" % version)

            # 4 byte tag size
            tag_size = _read_int(data[12:16])
            debug("tag size: %d" % tag_size)

            # 4 byte item count
            item_count = _read_int(data[16:20])
            debug("item count: %d" % item_count)

            # 4 byte flags
            flags = _read_int(data[20:24])
            debug("flags: %#x" % flags)
            if flags & IS_HEADER:
                raise InvalidTagError("found header at end of file")

            f.seek(-tag_size, 2)
            # tag size includes footer
            return f.read(tag_size - 32), item_count
        else:
            debug("no APE tag found")
            return None, 0

    def __iter__(self): return self.__dict.iteritems()
    def keys(self): return self.__dict.keys()
    def values(self): return self.__dict.values()
    def items(self): return self.__dict.items()

    def __contains__(self, k): return self.__dict.__contains__(APEKey(k))
    def __getitem__(self, k): return self.__dict[APEKey(k)]
    def __delitem__(self, k): del(self.__dict[APEKey(k)])
    def __setitem__(self, k, v):
        """This function tries (and usually succeeds) to guess at what
        kind of value you want to store. If you pass in a valid UTF-8
        or Unicode string, it treats it as a text value. If you pass
        in a list, it treats it as a list of string/Unicode values.
        If you pass in a string that is not valid UTF-8, it assumes
        it is a binary value."""
        if not isinstance(v, _APEValue):
            # let's guess at the content if we're not already a value...
            if isinstance(v, unicode):
                # unicode? we've got to be text.
                v = APEValue(_utf8(v), TEXT)
            elif isinstance(v, list):
                # list? text.
                v = APEValue("\0".join(map(_utf8, v)), TEXT)
            else:
                try: dummy = k.decode("utf-8")
                except UnicodeError:
                    # invalid UTF8 text, probably binary
                    v = APEValue(v, BINARY)
                else:
                    # valid UTF8, probably text
                    v = APEValue(v, TEXT)
        self.__dict[APEKey(k)] = v

    def write(self, filename = None):
        """Saves any changes you've made to the file, or to a different
        file if you specify one. Any existing tag will be removed."""
        filename = filename or self.filename
        f = file(filename, "ab+")
        offset = self._tag_start(f)

        f.seek(offset, 0)
        f.truncate()

        tags = [v._internal(k) for k, v in self]
        tags.sort(lambda a, b: cmp(len(a), len(b)))
        num_tags = len(tags)
        tags = "".join(tags)
        debug("writing %s" % str(tags))

        header = "APETAGEX%s%s" %(
            # version, tag size, item count, flags
            struct.pack("<4I", 2000, len(tags) + 32, num_tags,
                        HAS_HEADER | HAS_FOOTER | IS_HEADER),
            "\0" * 8)
        f.write(header)

        f.write(tags)

        footer = "APETAGEX%s%s" %(
            # version, tag size, item count, flags
            struct.pack("<4I", 2000, len(tags) + 32, num_tags,
                        HAS_HEADER | HAS_FOOTER),
            "\0" * 8)
        f.write(footer)
        f.close()

class APEKey(str):
    """An APE key is an ASCII string of length 2 to 255. The specification's
    case rules are silly, so this object is case-preserving but not
    case-sensitive, i.e. "album" == "Album"."""

    def __cmp__(self, o):
        return cmp(str(self).lower(), str(o).lower())
    
    def __eq__(self, o):
        return str(self).lower() == str(o).lower()
    
    def __hash__(self):
        return str.__hash__(self.lower())

    def __repr__(self): return "<APEKey %s>" % str.__repr__(self)

def APEValue(value, kind):
    """It is not recommended you construct APE values manually; instead
    use APETag's __setitem__."""
    if kind == TEXT: return APETextValue(value, kind)
    elif kind == BINARY: return APEBinaryValue(value, kind)
    elif kind == EXTERNAL: return APEExtValue(value, kind)
    else: raise ValueError("kind must be TEXT, BINARY, or EXTERNAL")

class _APEValue(object):
    def __init__(self, value, kind):
        self.kind = kind
        self.value = value

    def __len__(self): return len(self.value)
    def __str__(self): return self.value

    def _internal(self, key):
        return "%s%s\0%s" %(
            struct.pack("<2I", len(self.value), self.kind << 1),
            key, self.value)

class APETextValue(_APEValue):
    """APE text values are Unicode/UTF-8 strings. They can be accessed
    like strings (with a null seperating the values), or arrays of strings."""
    def __unicode__(self):
        return unicode(str(self), "utf-8")

    """Iterating over an APETextValue will iterate over the Unicode strings,
    not the characters in the string."""
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

    def __repr__(self):
        return "<APETextValue %r>" % list(self)

class APEBinaryValue(_APEValue):
    """Binary values may be converted to a string of bytes. They are
    used for anything not intended to be human-readable."""
    def __repr__(self):
        return "<APEBinaryValue (%d bytes)>" % len(self)

class APEExtValue(_APEValue):
    """An external value is a string containing a URI (http://..., file://...)
    that contains the actual value of the tag."""
    def __repr__(self):
        return "<APEExtValue ref=%s>" % len(self.value)

def _read_int(data):
    # ints in APE are LE
    return struct.unpack('<I', data)[0]

def _utf8(data):
    if isinstance(data, str):
        return data.decode("utf-8", "replace").encode("utf-8")
    elif isinstance(data, unicode):
        return data.encode("utf-8")
    else: raise TypeError("only unicode/str types can be converted to UTF-8")
