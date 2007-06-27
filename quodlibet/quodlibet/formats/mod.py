# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

from quodlibet.formats._audio import AudioFile

extensions = [
    '.669', '.amf', '.ams', '.dsm', '.far', '.it', '.med', '.mod', '.mt2',
    '.mtm', '.okt', '.s3m', '.stm', '.ult', '.gdm', '.xm']
try:
    import ctypes
    _modplug = ctypes.cdll.LoadLibrary("libmodplug.so.0")
    _modplug.ModPlug_GetName.restype = ctypes.c_char_p
except (ImportError, OSError):
    extensions = []

class ModFile(AudioFile):

    format = "MOD/XM/IT"

    def __init__(self, filename):
        size = os.path.getsize(filename)
        data = file(filename).read()
        f = _modplug.ModPlug_Load(data, len(data))
        if not f: raise IOError("%r not a valid MOD file" % filename)
        self["~#length"] = _modplug.ModPlug_GetLength(f) // 1000
        title = _modplug.ModPlug_GetName(f) or os.path.basename(filename)
        try: self["title"] = title.decode('utf-8')
        except UnicodeError: self["title"] = title.decode("iso-8859-1")
        _modplug.ModPlug_Unload(f)
        self.sanitize(filename)

    def write(self):
        pass

    def reload(self, *args):
        artist = self.get("artist")
        super(ModFile, self).reload(*args)
        if artist is not None: self.setdefault("artist", artist)

    def can_change(self, k=None):
        if k is None: return ["artist"]
        else: return k == "artist"

info = ModFile

