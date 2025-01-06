# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from mutagen.monkeysaudio import MonkeysAudio

from ._audio import translate_errors
from ._apev2 import APEv2File


class MonkeysAudioFile(APEv2File):
    format = "Monkey's Audio"

    def __init__(self, filename):
        with translate_errors():
            audio = MonkeysAudio(filename)
        super().__init__(filename, audio)
        self["~#length"] = int(audio.info.length)
        self["~#channels"] = audio.info.channels
        self["~#samplerate"] = audio.info.sample_rate
        if hasattr(audio.info, "bits_per_sample"):
            self["~#bitdepth"] = audio.info.bits_per_sample
        self.sanitize(filename)


loader = MonkeysAudioFile
types = [MonkeysAudioFile]
extensions = [".ape"]
