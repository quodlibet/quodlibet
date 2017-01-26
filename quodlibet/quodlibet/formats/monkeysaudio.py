# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from mutagen.monkeysaudio import MonkeysAudio

from ._audio import translate_errors
from ._apev2 import APEv2File


class MonkeysAudioFile(APEv2File):
    format = "Monkey's Audio"

    def __init__(self, filename):
        with translate_errors():
            audio = MonkeysAudio(filename)
        super(MonkeysAudioFile, self).__init__(filename, audio)
        self["~#length"] = int(audio.info.length)
        self["~#channels"] = audio.info.channels
        self.sanitize(filename)

loader = MonkeysAudioFile
types = [MonkeysAudioFile]
extensions = [".ape"]
