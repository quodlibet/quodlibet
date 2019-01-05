# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import struct

from ._audio import AudioFile, translate_errors

# VGM and GD3 SPECs:
# http://www.smspower.org/uploads/Music/vgmspec170.txt
# http://www.smspower.org/uploads/Music/gd3spec100.txt
GD3_TAG_PTR_POS = 0x14
GD3_TAG_PTR_SIZE = 4

GD3_ENGLISH_TITLE = 0
GD3_JAPANESE_TITLE = 1
GD3_ENGLISH_GAME = 2
GD3_JAPANESE_GAME = 3
GD3_ENGLISH_SYSTEM = 4
GD3_JAPANESE_SYSTEM = 5
GD3_ENGLISH_ARTIST = 6
GD3_JAPANESE_ARTIST = 7
GD3_DATE = 8
GD3_DUMPER = 9
GD3_COMMENT = 10


class VgmFile(AudioFile):
    format = "VGM"
    mimes = []

    def __init__(self, filename):
        with translate_errors():
            with open(filename, "rb") as h:
                header = h.read(64)
                if len(header) != 64 or header[:4] != b"Vgm ":
                    # filename useful to show (helps w/ faulty VGM files.)
                    raise Exception(filename + " not a VGM file")

                samples_to_sec = lambda s: s / 44100.
                samples = struct.unpack('<i', header[24:28])[0]
                loop_offset = struct.unpack('<i', header[28:32])[0]
                loop_samples = struct.unpack('<i', header[32:36])[0]

                # this should match libgme
                length = samples_to_sec(samples)
                if length <= 0:
                    length = 150
                elif loop_offset:
                    # intro + 2 loops
                    length += samples_to_sec(loop_samples)

                self["~#length"] = length

                gd3_position = struct.unpack('<i',
                                             header[GD3_TAG_PTR_POS:
                                                    GD3_TAG_PTR_POS
                                                    + GD3_TAG_PTR_SIZE])[0]
                h.seek(GD3_TAG_PTR_POS + gd3_position)
                self.update(parse_gd3(h.read()))

        self.sanitize(filename)

    def write(self):
        pass

    def reload(self, *args):
        title = self.get("title")
        super(VgmFile, self).reload(*args)
        if title is not None:
            self.setdefault("title", title)

    def can_change(self, k=None):
        if k is None:
            return ["title"]
        else:
            return k == "title"


def parse_gd3(data):
    tags = {}
    if data[0:4] != b'Gd3 ':
        print('Invalid Gd3, Missing Header...')
        return tags

    version = data[4:8]
    # Should be [0x00, 0x10, 0x00, 0x00] currently.
    # We should hold onto it for possible branching if standards change.

    gd3_length = struct.unpack('<i', data[8:12])[0]
    # Length of gd3 footer. This means we can actually add more tags to the end
    # with APETAG at some point. (Or at least consider...)

    entries = data[12:12+gd3_length].decode('utf-16').split('\0')

    tags["title"] = entries[GD3_ENGLISH_TITLE] \
        if (entries[GD3_ENGLISH_TITLE] == entries[GD3_JAPANESE_TITLE]) \
        else \
        '\n'.join(filter(None, [entries[GD3_ENGLISH_TITLE],
                                entries[GD3_JAPANESE_TITLE]]))

    tags["artist"] = '\n'.join(filter(None, [entries[GD3_ENGLISH_ARTIST],
                                             entries[GD3_JAPANESE_ARTIST]]))
    tags["console"] = '\n'.join(filter(None, [entries[GD3_ENGLISH_SYSTEM],
                                              entries[GD3_JAPANESE_SYSTEM]]))
    tags["album"] = '\n'.join(filter(None, [entries[GD3_ENGLISH_GAME],
                                            entries[GD3_JAPANESE_GAME]]))
    tags["date"] = entries[GD3_DATE]
    tags["dumper"] = entries[GD3_DUMPER]
    tags["comment"] = entries[GD3_COMMENT]
    return tags


loader = VgmFile
types = [VgmFile]
extensions = [".vgm"]
