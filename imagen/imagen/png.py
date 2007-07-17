import struct
import zlib

class error(IOError):
    def __init__(self, str, filename=None):
        IOError.__init__(self, str)
        self.filename = filename

class _Chunk(object):
    type = ""
    data = ""

    def __init__(self, fileobj):
        length_data = fileobj.read(4)
        if not length_data:
            raise EOFError
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
            try: self.chunks.append(_Chunk(fileobj))
            except EOFError:
                break

    def __repr__(self):
        return "%s(%r)" % (type(self).__name__, self.chunks)

__all__ = ["PNG"]
