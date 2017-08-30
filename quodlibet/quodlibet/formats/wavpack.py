# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from mutagen.wavpack import WavPack

from ._audio import translate_errors
from ._apev2 import APEv2File


class WavpackFile(APEv2File):
    format = "WavPack"
    mimes = ["audio/x-wavpack"]

    def __init__(self, filename):
        with translate_errors():
            audio = WavPack(filename)
        super(WavpackFile, self).__init__(filename, audio)
        self["~#length"] = audio.info.length
        self["~#channels"] = audio.info.channels
        self.sanitize(filename)

loader = WavpackFile
types = [WavpackFile]
extensions = [".wv"]
