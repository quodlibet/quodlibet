# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from mutagen.aac import AAC

from ._audio import AudioFile, translate_errors

extensions = [".aac", ".adif", ".adts"]


class AACFile(AudioFile):
    """ADTS/ADIF files"""

    format = "AAC"
    mimes = ["audio/x-aac"]
    fill_length = True

    def __init__(self, filename):
        with translate_errors():
            audio = AAC(filename)
        self["~#length"] = audio.info.length
        self["~#bitrate"] = int(audio.info.bitrate / 1000)
        if audio.info.channels:
            self["~#channels"] = audio.info.channels
        self["~#samplerate"] = audio.info.sample_rate
        self.sanitize(filename)

    def write(self):
        pass

    def reload(self, *args):
        title = self.get("title")
        super().reload(*args)
        if title is not None:
            self.setdefault("title", title)

    def can_change(self, k=None):
        if k is None:
            return ["title"]
        return k == "title"


loader = AACFile
types = [AACFile]
