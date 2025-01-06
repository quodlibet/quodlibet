# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from senf import fsnative, path2fsn

from ._audio import AudioFile


extensions: list[str] = []


class RemoteFile(AudioFile):
    is_file = False
    fill_metadata = True

    format = "Remote File"

    def __init__(self, uri):
        assert not isinstance(uri, bytes)
        self["~uri"] = str(uri)
        self.sanitize(fsnative(self["~uri"]))

    def __getitem__(self, key):
        # we used to save them with the wrong type
        value = super().__getitem__(key)
        if key in ("~filename", "~mountpoint") and not isinstance(value, fsnative):
            value = path2fsn(value)

        return value

    def rename(self, newname):
        pass

    def reload(self):
        pass

    def exists(self):
        return True

    def valid(self):
        return True

    def mounted(self):
        return True

    def write(self):
        pass

    def can_change(self, k=None):
        if k is None:
            return []
        else:
            return False

    @property
    def key(self):
        return self["~uri"]


loader = RemoteFile
types = [RemoteFile]
