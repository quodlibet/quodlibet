# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import struct
import os

from senf import path2fsn, fsn2text
from ._audio import AudioFile, translate_errors
from quodlibet.util.dprint import print_d
from quodlibet.util import list_unique

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
    mimes: list[str] = []

    def __init__(self, filename):
        with translate_errors():
            with open(filename, "rb") as h:
                header = h.read(64)
                if len(header) != 64 or header[:4] != b"Vgm ":
                    # filename useful to show (helps w/ faulty VGM files.)
                    raise Exception(filename + " not a VGM file")

                def samples_to_sec(s):
                    return s / 44100.0

                samples = struct.unpack("<i", header[24:28])[0]
                loop_offset = struct.unpack("<i", header[28:32])[0]
                loop_samples = struct.unpack("<i", header[32:36])[0]

                # this should match libgme
                length = samples_to_sec(samples)
                if length <= 0:
                    length = 150
                elif loop_offset:
                    # intro + 2 loops
                    length += samples_to_sec(loop_samples)

                self["~#length"] = length

                gd3_position = struct.unpack(
                    "<i", header[GD3_TAG_PTR_POS : GD3_TAG_PTR_POS + GD3_TAG_PTR_SIZE]
                )[0]
                h.seek(GD3_TAG_PTR_POS + gd3_position)
                self.update(parse_gd3(h.read()))

        self.setdefault("title", fsn2text(path2fsn(os.path.basename(filename)[:-4])))
        self.sanitize(filename)

    def write(self):
        pass

    def can_change(self, k=None):
        if k is None:
            return ["title"]
        return k == "title"


def parse_gd3(data):
    tags = {}
    if data[0:4] != b"Gd3 ":
        print_d("Invalid Gd3, Missing Header...")
        return tags

    # version = data[4:8]
    # Should be [0x00, 0x10, 0x00, 0x00] currently.
    # We should hold onto it for possible branching if standards change.

    gd3_length = struct.unpack("<i", data[8:12])[0]
    # Length of gd3 footer. This means we can actually add more tags to the end
    # with APETAG at some point. (Or at least consider...)

    entries = data[12 : 12 + gd3_length].decode("utf-16-le").split("\0")

    if len(entries) > GD3_JAPANESE_TITLE:
        titles = gd3_filter_entries(
            [entries[GD3_ENGLISH_TITLE], entries[GD3_JAPANESE_TITLE]]
        )
        if len(titles) > 0:
            tags["title"] = "\n".join(titles)

    if len(entries) > GD3_JAPANESE_ARTIST:
        artists = gd3_filter_entries(
            [entries[GD3_ENGLISH_ARTIST], entries[GD3_JAPANESE_ARTIST]]
        )
        if len(artists) > 0:
            tags["artist"] = "\n".join(artists)

    if len(entries) > GD3_JAPANESE_SYSTEM:
        consoles = gd3_filter_entries(
            [entries[GD3_ENGLISH_SYSTEM], entries[GD3_JAPANESE_SYSTEM]]
        )
        if len(consoles) > 0:
            tags["console"] = "\n".join(consoles)

    if len(entries) > GD3_JAPANESE_GAME:
        games = gd3_filter_entries(
            [entries[GD3_ENGLISH_GAME], entries[GD3_JAPANESE_GAME]]
        )
        if len(games) > 0:
            tags["album"] = "\n".join(games)

    if len(entries) > GD3_DATE and entries[GD3_DATE] != "":
        tags["date"] = entries[GD3_DATE]

    if len(entries) > GD3_DUMPER and entries[GD3_DUMPER] != "":
        tags["dumper"] = entries[GD3_DUMPER]

    if len(entries) > GD3_COMMENT:
        tags["comment"] = entries[GD3_COMMENT]

    return tags


def gd3_filter_entries(entries):
    # First, filter out empty strings...
    filtered = list(filter(None, entries))
    if len(filtered) == 0:
        return filtered

    # Then, filter out any duplicate strings...
    filtered = list_unique(filtered)
    return sorted(filtered)


loader = VgmFile
types = [VgmFile]
extensions = [".vgm"]
