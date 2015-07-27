# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import wave

from quodlibet.util.path import fsdecode

from ._audio import AudioFile


extensions = [".wav"]


class WAVEFile(AudioFile):
    format = "WAVE"
    mimes = ["audio/wav", "audio/x-wav", "audio/wave"]

    def __init__(self, filename):
        with open(filename, "rb") as h:
            f = wave.open(h)
            self["~#length"] = f.getnframes() / f.getframerate()
        self.sanitize(filename)

    def sanitize(self, filename):
        super(WAVEFile, self).sanitize(filename)
        self["title"] = fsdecode(os.path.splitext(
            os.path.basename(self["~filename"]))[0])

    def write(self):
        pass

    def can_change(self, k=None):
        if k is None:
            return ["artist"]
        else:
            return k == "artist"

info = WAVEFile
types = [WAVEFile]
