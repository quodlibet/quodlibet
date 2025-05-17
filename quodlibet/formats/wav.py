# Copyright 2006 Joe Wreschnig
#           2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import wave

from senf import fsn2text

from ._audio import AudioFile, translate_errors


extensions = [".wav"]


class WAVEFile(AudioFile):
    format = "WAVE"
    mimes = ["audio/wav", "audio/x-wav", "audio/wave"]

    def __init__(self, filename):
        with translate_errors():
            with open(filename, "rb") as h:
                f = wave.open(h)
                self["~#length"] = float(f.getnframes()) / f.getframerate()
                self["~#channels"] = f.getnchannels()
                self["~#samplerate"] = f.getframerate()
                self["~#bitdepth"] = f.getsampwidth() * 8
        self.sanitize(filename)

    def sanitize(self, filename=None):
        super().sanitize(filename)
        self["title"] = fsn2text(
            os.path.splitext(os.path.basename(self["~filename"]))[0]
        )

    def write(self):
        pass

    def can_change(self, k=None):
        if k is None:
            return ["artist"]
        return k == "artist"


loader = WAVEFile
types = [WAVEFile]
