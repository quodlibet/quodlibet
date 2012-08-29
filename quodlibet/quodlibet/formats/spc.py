# Copyright 2007 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from quodlibet.formats._audio import AudioFile

extensions = [".spc"]

class SPCFile(AudioFile):
    format = "SPC700 DSP Data"

    def __init__(self, filename):
        h = open(filename, "rb")
        try:
            head = h.read(46)
            if len(head) != 46 or head[:27] != 'SNES-SPC700 Sound File Data':
                raise IOError("Not a valid SNES-SPC700 file")

            if head[35] == '\x1a':
                data = h.read(210)
                if len(data) == 210:
                    self.update(parse_id666(data))
        finally:
            h.close()

        self.setdefault("title", os.path.basename(filename)[:-4])
        self.sanitize(filename)

    def write(self):
        pass

    def can_change(self, k=None):
        TAGS = ["artist", "album", "title", "comments"]
        if k is None: return TAGS
        else: return k in TAGS


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
    if data[130] < 'A':
        try:
            tags["~#length"] = int(data[123:126].strip("\x00"))
        except ValueError:
            pass
        tags["artist"] = data[131:163]
    else:
        tags["artist"] = data[130:162]

    for k in tags.keys():
        if k[:2] == "~#":
            continue
        tags[k] = tags[k].replace("\x00", "").decode("ascii", "ignore")
        if not tags[k]:
            del tags[k]

    return tags


info = SPCFile
types = [SPCFile]
