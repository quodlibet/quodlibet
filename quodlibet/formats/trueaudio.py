# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Niklas Janlert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from mutagen.trueaudio import TrueAudio

from ._id3 import ID3File


class TrueAudioFile(ID3File):
    format = "True Audio"
    mimes = ["audio/x-tta"]
    Kind = TrueAudio

    def _parse_info(self, info):
        self["~#length"] = info.length
        self["~#samplerate"] = info.sample_rate


loader = TrueAudioFile
types = [TrueAudioFile]
extensions = [".tta"]
