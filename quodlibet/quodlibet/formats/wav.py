# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import wave

from quodlibet.formats._audio import AudioFile

extensions = [".wav"]

class WAVEFile(AudioFile):
    format = "WAVE"
    mimes = ["audio/wav", "audio/x-wav", "audio/wave"]

    def __init__(self, filename):
        f = wave.open(filename, "rb")
        self["~#length"] = f.getnframes() // f.getframerate()
        self.sanitize(filename)

    def sanitize(self, filename):
        super(WAVEFile, self).sanitize(filename)
        self["title"] = os.path.basename(self["~filename"])[:-4]

    def write(self):
        pass

    def can_change(self, k=None):
        if k is None: return ["artist"]
        else: return k == "artist"

info = WAVEFile
types =[WAVEFile]
