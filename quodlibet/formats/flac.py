# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, stat
import gst
from formats._vorbis import VCFile
import util

try: import flac.metadata, flac.decoder
except: extensions = []
else:
    if gst.element_factory_make('flacdec'): extensions = [".flac"]
    else: extensions = []

class FLACFile(VCFile):
    def __init__(self, filename):
        if not os.path.exists(filename):
            raise IOError("%s does not exist" % filename)
        chain = flac.metadata.Chain()
        chain.read(filename)
        it = flac.metadata.Iterator()
        it.init(chain)
        vc = None
        while True:
            if it.get_block_type() == flac.metadata.VORBIS_COMMENT:
                block = it.get_block()
                vc = flac.metadata.VorbisComment(block)
            elif it.get_block_type() == flac.metadata.STREAMINFO:
                info = it.get_block().data.stream_info
                self["~#length"] = (info.total_samples // info.sample_rate)
            if not it.next(): break

        if vc:
            for k in vc.comments:
                parts = k.split("=")
                key = parts[0].lower()
                val = util.decode("=".join(parts[1:]))
                if key in self: self[key] += "\n" + val
                else: self[key] = val
        self.sanitize(filename)

    def write(self):
        chain = flac.metadata.Chain()
        chain.read(self['~filename'])
        it = flac.metadata.Iterator()
        it.init(chain)
        vc = None
        while True:
            if it.get_block_type() == flac.metadata.VORBIS_COMMENT:
                block = it.get_block()
                vc = flac.metadata.VorbisComment(block)
                break
            if not it.next(): break

        if vc:
            keys = [k.split("=")[0] for k in vc.comments]
            for k in keys: del(vc.comments[k])
            for key in self.realkeys():
                value = self.list(key)
                for line in value:
                    vc.comments[key] = util.encode(line)
            self._prep_write(vc.comments)
            chain.write(True, True)

info = FLACFile
