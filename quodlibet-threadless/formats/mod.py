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

info = ModFile
player = None
