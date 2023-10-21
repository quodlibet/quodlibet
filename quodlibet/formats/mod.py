# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import ctypes

from quodlibet.util import load_library

from ._audio import AudioFile, translate_errors


extensions = [
    ".669", ".amf", ".ams", ".dsm", ".far", ".it", ".med", ".mod", ".mt2",
    ".mtm", ".okt", ".s3m", ".stm", ".ult", ".gdm", ".xm"]

try:
    _modplug = load_library(
        ["libmodplug.so.1", "libmodplug.so.0", "libmodplug-1.dll"])[0]
except OSError:
    extensions = []
else:
    _modplug.ModPlug_GetName.argtypes = [ctypes.c_void_p]
    _modplug.ModPlug_GetName.restype = ctypes.c_char_p

    _modplug.ModPlug_Load.argtypes = [ctypes.c_void_p, ctypes.c_int]
    _modplug.ModPlug_Load.restype = ctypes.c_void_p

    _modplug.ModPlug_GetLength.argtypes = [ctypes.c_void_p]
    _modplug.ModPlug_GetLength.restype = ctypes.c_int

    _modplug.ModPlug_Unload.argtypes = [ctypes.c_void_p]
    _modplug.ModPlug_Unload.restype = None


class ModFile(AudioFile):

    format = "MOD/XM/IT"

    def __init__(self, filename):
        with translate_errors():
            data = open(filename, "rb").read()
            f = _modplug.ModPlug_Load(data, len(data))
            if not f:
                raise IOError("%r not a valid MOD file" % filename)
            self["~#length"] = _modplug.ModPlug_GetLength(f) // 1000
            title = _modplug.ModPlug_GetName(f) or os.path.basename(filename)
            try:
                self["title"] = title.decode("utf-8")
            except UnicodeError:
                self["title"] = title.decode("iso-8859-1")
            _modplug.ModPlug_Unload(f)

        self.sanitize(filename)

    def write(self):
        pass

    def reload(self, *args):
        artist = self.get("artist")
        super().reload(*args)
        if artist is not None:
            self.setdefault("artist", artist)

    def can_change(self, k=None):
        if k is None:
            return ["artist"]
        else:
            return k == "artist"

loader = ModFile
types = [ModFile]
