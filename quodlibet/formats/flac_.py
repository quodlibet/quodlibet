# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gst
from formats._vorbis import VCFile
import util

try: import mutagen.flac
except: extensions = []
else:
    if gst.element_factory_make('flacdec'): extensions = [".flac"]
    else: extensions = []

class FLACFile(VCFile):
    format = "FLAC"

    def __init__(self, filename):
        f = mutagen.flac.FLAC(filename)
        self["~#length"] = int(f.info.length)
        for key, value in f.vc.items(): self[key] = "\n".join(value)
        self.sanitize(filename)

    def write(self):
        f = mutagen.flac.FLAC(self["~filename"])
        if not f.vc: f.add_vorbiscomment()
        del(f.vc[:])
        for key in self.realkeys(): f.vc[key] = self.list(key)
        self._prep_write(f.vc)
        f.save()
        self.sanitize()

info = FLACFile
