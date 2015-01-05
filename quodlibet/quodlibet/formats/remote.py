# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from quodlibet.formats._audio import AudioFile
from quodlibet.util.path import fsnative, is_fsnative
from quodlibet.util.uri import URI

extensions = []


class RemoteFile(AudioFile):
    is_file = False
    fill_metadata = True

    format = "Remote File"

    def __init__(self, uri):
        self["~uri"] = str(URI(uri))
        self.sanitize(fsnative(unicode(self["~uri"])))

    def __getitem__(self, key):
        # we used to save them with the wrong type
        value = super(RemoteFile, self).__getitem__(key)
        if key in ("~filename", "~mountpoint") and not is_fsnative(value):
            if os.name == "nt":
                value = unicode(value)
            else:
                value = value.encode("utf-8")

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
        raise TypeError("RemoteFiles do not support writing!")

    def can_change(self, k=None):
        if k is None:
            return []
        else:
            return False

    key = property(lambda self: self["~uri"])

info = RemoteFile
types = [RemoteFile]
