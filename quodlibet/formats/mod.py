# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from formats.audio import AudioFile, AudioPlayer

try: import modplug
except ImportError: extensions = []
# Based on the supported format list at http://www.linuks.mine.nu/modplugplay
else: extensions = ['.669', '.amf', '.ams', '.dbm', '.dmf', '.dsm', '.far',
                    '.it', '.j2b', '.mdl', '.med', '.mod', '.mt2', '.mtm',
                    '.okt', '.psm', '.ptm', '.s3m', '.stm', '.ult', '.umx',
                    '.xm']

class ModFile(AudioFile):
    def __init__(self, filename):
        f = modplug.ModFile(filename)
        self["~#length"] = f.length // 1000
        try: self["title"] = f.title.decode("utf-8")
        except UnicodeError: self["title"] = f.title.decode("iso-8859-1")
        self.sanitize(filename)

    def write(self):
        raise TypeError("ModFiles do not support writing!")

    def can_change(self, k = None):
        if k is None: return []
        else: return False

class ModPlayer(AudioPlayer):
    def __init__(self, dev, song):
        AudioPlayer.__init__(self)
        self.audio = modplug.ModFile(song["~filename"])
        self.length = self.audio.length
        self.dev = dev
        self.dev.set_info(44100, 2)

    def __iter__(self): return self

    def seek(self, ms):
        self.audio.seek(ms)

    def next(self):
        if self.stopped: raise StopIteration
        else:
            s = self.audio.read(256)
            if s: self.dev.play(s)
            else: raise StopIteration
        return int(self.audio.position)

info = ModFile
player = ModPlayer
