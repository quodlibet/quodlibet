import struct
import zlib

try: from cStringIO import StringIO
except ImportError: from StringIO import StringIO

import imagen


class error(IOError):
    def __init__(self, str, filename=None):
        IOError.__init__(self, str)
        self.filename = filename

SORT_ORDER = {
    "IDHR": 0,
    "cHRM": 50,
    "gAMA": 50,
    "iCCP": 50,
    "sBIT": 50,
    "PLTE": 100,
    "bKGD": 150,
    "hIST": 150,
    "tRNS": 150,
    "pHYs": 150,
    "IDAT": 500,
    "IEND": 1000
    }


class _Chunk(object):
    type = ""
    data = ""

    def __init__(self, fileobj):
        try:
            length_data = fileobj.read(4)
        except AttributeError:
            crc = struct.pack(">i", zlib.crc32(fileobj))
            length = len(fileobj)
            fileobj = StringIO(fileobj + crc)
        else:
            length, = struct.unpack(">I", length_data)
            self.type = fileobj.read(4)
            
        self.data = fileobj.read(length)
        crc, = struct.unpack(">i", fileobj.read(4))
        real_crc = zlib.crc32(self.type + self.data)

        if crc != real_crc:
            raise error("Invalid CRC in chunk: %r != %r" % (crc, real_crc),
                        fileobj.name)

    def __repr__(self):
        return "%s(type=%r, %r bytes)" % (
            type(self).__name__, self.type, len(self.data))

class tEXt(_Chunk):
    def __init__(self, *args, **kwargs):
        super(tEXt, self).__init__(*args, **kwargs)

    def __get_keyword(self):
        keyword, string = self.data.split("\x00", 1)
        return keyword.decode("iso-8859-1")

    def __set_keyword(self, keyword):
        if len(keyword) >= 80 or len(keyword) < 1 or "\x00" in keyword:
            raise ValueError("Invalid keyword %r" % keyword)
        old_keyword, string = self.data.split("\x00", 1)
        self.data = imagen.latin1(keyword) + "\x00" + string

    keyword = property(__get_keyword, __set_keyword)

    def __get_string(self):
        keyword, string = self.data.split("\x00", 1)
        return string.decode("iso-8859-1")

    def __set_string(self, string):
        if "\x00" in string:
            raise ValueError("Invalid string %r" % string)
        keyword, old_string = self.data.split("\x00", 1)
        self.data = keyword + "\x00" + imagen.latin1(string)

    string = property(__get_string, __set_string)

class PNG(object):
    _mime = ["image/png"]
    _extensions = [".png"]

    def __init__(self, filename):
        self.filename = filename
        self.chunks = []
        fileobj = file(filename, "rb")

        header = fileobj.read(8)
        if header != "\x89\x50\x4e\x47\x0d\x0a\x1a\x0a":
            raise error("file has no PNG header", filename)

        while True:
            length = fileobj.read(4)
            type = fileobj.read(4)
            if type:
                fileobj.seek(-8, 1)
                Kind = Chunks.get(type, _Chunk)
                self.chunks.append(Kind(fileobj))
            else:
                break

    def __getitem__(self, key):
        chunks = []
        for chunk in self.chunks:
            if chunk.type == key:
                chunks.append(key)
        if not chunks:
            raise KeyError(key)
        else:
            return chunks
        

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.chunks)

Chunks = dict(
    [(k,v) for (k,v) in globals().items()
     if len(k) == 4 and isinstance(v, type) and issubclass(v, _Chunk)])
del(k); del(v)


__all__ = ["PNG", "Chunks"]
