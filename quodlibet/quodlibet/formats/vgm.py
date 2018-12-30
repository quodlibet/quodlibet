# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""http://www.smspower.org/uploads/Music/vgmspec161.txt"""

import struct

from ._audio import AudioFile, translate_errors


class VgmFile(AudioFile):
    format = "VGM"
    mimes = []

    def __init__(self, filename):
        with translate_errors():
            with open(filename, "rb") as h:
                header = h.read(64)
                if len(header) != 64 or header[:4] != b"Vgm ":
                    raise Exception("Not a VGM file")

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


loader = VgmFile
types = [VgmFile]
extensions = [".vgm"]
