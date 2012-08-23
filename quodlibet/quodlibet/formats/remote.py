# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.formats._audio import AudioFile
from quodlibet.util.uri import URI

extensions = []

class RemoteFile(AudioFile):
    is_file = False
    fill_metadata = True

    format = "Remote File"

    def __init__(self, uri):
        self["~uri"] = self["~filename"] = str(URI(uri))
        self["~mountpoint"] = ""
        self.sanitize(uri)

    def rename(self, newname): pass
    def reload(self): pass
    def exists(self): return True
    def valid(self): return True
    def mounted(self): return True

    def write(self):
        raise TypeError("RemoteFiles do not support writing!")

    def can_change(self, k = None):
        if k is None: return []
        else: return False

    key = property(lambda self: self["~uri"])

info = RemoteFile
types = [RemoteFile]
