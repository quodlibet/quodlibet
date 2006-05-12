# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst

from formats._vorbis import VCFile

try:
    import mutagen.flac
except ImportError:
    extensions = []
else:
    try: gst.element_factory_make('flacdec')
    except gst.PluginNotFoundError: extensions = []
    else: extensions = [".flac"]

class FLACFile(VCFile):
    format = "FLAC"

    def __init__(self, filename):
        f = mutagen.flac.FLAC(filename)
        self["~#length"] = int(f.info.length)
        for key, value in (f.tags or {}).items():
            self[key] = "\n".join(value)
        self._post_read()
        self.sanitize(filename)

    def write(self):
        f = mutagen.flac.FLAC(self["~filename"])
        if f.tags is None: f.add_tags()
        self._prep_write(f.tags)
        for key in self.realkeys(): f.tags[key] = self.list(key)
        f.save()
        self.sanitize()

info = FLACFile
