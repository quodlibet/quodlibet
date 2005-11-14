# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import sys
import urllib
from formats._audio import AudioFile
if sys.version_info < (2, 4): from sets import Set as set

extensions = []

class RemoteFile(AudioFile):
    is_file = False
    fill_metadata = True

    format = "Remote File"

    def __init__(self, uri):
        # FIXME: Add tests!
        type, location = urllib.splittype(uri)
        host, path = urllib.splithost(location)
        # Check to see if the URL is unquoted...
        if set(";?:@&=+$ ,").intersection(path): path = urllib.quote(path)
        uri = ":".join([type, "//" + host + path])
        self["~uri"] = self["~filename"] = uri
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

info = RemoteFile


