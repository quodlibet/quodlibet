# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

try:
    from mutagen.dsf import DSF
except ImportError:
    DSF = None

from ._id3 import ID3File


class DSFFile(ID3File):
    format = "DSF"

    mimes = ["audio/dsf"]
    Kind = DSF

    def _parse_info(self, info):
        self["~#length"] = info.length
        self["~#bitrate"] = int(info.bitrate / 1000)
        self["~#channels"] = info.channels
        self["~#samplerate"] = info.sample_rate
        self["~#bitdepth"] = info.bits_per_sample

loader = DSFFile
types = [DSFFile]

if DSF:
    extensions = [".dsf"]
else:
    extensions = []
