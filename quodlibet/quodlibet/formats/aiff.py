# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from mutagen.aiff import AIFF

from ._id3 import ID3File

extensions = [".aif", ".aiff", ".aifc"]


class AIFFFile(ID3File):
    format = "AIFF"

    mimes = ["audio/x-aiff", "audio/aiff"]
    Kind = AIFF

    def _parse_info(self, info):
        self["~#length"] = info.length
        self["~#bitrate"] = int(info.bitrate / 1000)
        self["~#channels"] = info.channels


loader = AIFFFile
types = [AIFFFile]
