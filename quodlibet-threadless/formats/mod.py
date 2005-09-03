# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst
from formats.audio import AudioFile

try: import modplug
except ImportError: extensions = []
else:
    if gst.element_factory_make("mikmod"):
        extensions = ['.669', '.amf', '.ams', '.dsm', '.far', '.it', '.med',
                      '.mod', '.mt2', '.mtm', '.okt', '.s3m', '.stm', '.ult',
                      '.gdm', '.xm']
    else: extensions = []

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

