# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst
from formats._vorbis import VCFile

try: import ogg.vorbis
except ImportError: extensions = []
else:
    if gst.element_factory_make('vorbisdec'): extensions = [".ogg"]
    else: extensions = []

class OggFile(VCFile):

    format = "Ogg Vorbis"

    def __init__(self, filename):
        f = ogg.vorbis.VorbisFile(filename)
        for k, v in f.comment().as_dict().iteritems():
            if not isinstance(v, list): v = [v]
            v = u"\n".join(map(unicode, v))
            self[k.lower()] = v

        self["~#length"] = int(f.time_total(-1))
        self["~#bitrate"] = int(f.bitrate(-1))
        self.sanitize(filename)

    def write(self):
        f = ogg.vorbis.VorbisFile(self['~filename'])
        comments = f.comment()
        comments.clear()
        for key in self.realkeys():
            value = self.list(key)
            for line in value: comments[key] = line
        self._prep_write(comments)
        comments.write_to(self['~filename'])
        self.sanitize()

info = OggFile
