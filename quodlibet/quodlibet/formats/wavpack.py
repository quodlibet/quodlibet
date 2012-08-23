# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.formats._apev2 import APEv2File

extensions = [".wv"]
try:
    from mutagen.wavpack import WavPack
except ImportError:
    extensions = []

class WavpackFile(APEv2File):
    format = "WavPack"
    mimes = ["audio/x-wavpack"]
    
    def __init__(self, filename):
        audio = WavPack(filename)
        super(WavpackFile, self).__init__(filename, audio)
        self["~#length"] = int(audio.info.length)
        self.sanitize(filename)

info = WavpackFile
types = [WavpackFile]
