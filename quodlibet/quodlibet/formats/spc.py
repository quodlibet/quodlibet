# -*- coding: utf-8 -*-
# Copyright 2007 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from senf import path2fsn, fsn2text

from quodlibet.compat import getbyte, listkeys
from ._audio import AudioFile, translate_errors

extensions = [".spc"]


class SPCFile(AudioFile):
    format = "SPC700"

    def __init__(self, filename):
        with translate_errors():
            with open(filename, "rb") as h:
                head = h.read(46)
                if len(head) != 46 or \
                        head[:27] != b'SNES-SPC700 Sound File Data':
                    raise IOError("Not a valid SNES-SPC700 file")

                if getbyte(head, 35) == b'\x1a':
                    data = h.read(210)
                    if len(data) == 210:
                        self.update(parse_id666(data))

        self.setdefault(
            "title", fsn2text(path2fsn(os.path.basename(filename)[:-4])))
        self.sanitize(filename)

    def write(self):
        pass

    def can_change(self, k=None):
        TAGS = ["artist", "album", "title", "comments"]
        if k is None:
            return TAGS
        else:
            return k in TAGS


def parse_id666(data):
    #http://snesmusic.org/files/spc_file_format.txt

    tags = {}

    tags["title"] = data[:32]
    tags["album"] = data[32:64]
    tags["dumper"] = data[64:80]
    tags["comments"] = data[80:112]

    # Artist differs based on binary or text mode, which is implicit.
    # Instead of detecting "perfectly", we'll just detect enough for
    # the "artist" field. This fails for artist names that begin with
    # numbers or symbols less than ascii value A.
    if getbyte(data, 130) < b'A':
        try:
            tags["~#length"] = int(data[123:126].strip(b"\x00"))
        except ValueError:
            pass
        tags["artist"] = data[131:163]
    else:
        tags["artist"] = data[130:162]

    for k in listkeys(tags):
        if k[:2] == "~#":
            continue
        tags[k] = tags[k].replace(b"\x00", b"").decode("ascii", "ignore")
        if not tags[k]:
            del tags[k]

    return tags


loader = SPCFile
types = [SPCFile]
