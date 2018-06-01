# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Niklas Janlert
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from mutagen.mp3 import MP3

from ._id3 import ID3File

extensions = [".mp3", ".mp2", ".mp1", ".mpg", ".mpeg"]


class MP3File(ID3File):
    format = "MPEG-1/2"
    mimes = ["audio/mp3", "audio/x-mp3", "audio/mpeg", "audio/mpg",
             "audio/x-mpeg"]
    Kind = MP3

    def _parse_info(self, info):
        self["~#length"] = info.length
        self["~#bitrate"] = int(info.bitrate / 1000)
        self["~format"] = u"MP%d" % info.layer
        self["~#channels"] = info.channels
        self["~#samplerate"] = info.sample_rate

        encoder, brm = info.encoder_info, info.bitrate_mode
        brm = {1: u"CBR", 2: u"VBR", 3: u"ABR"}.get(brm, u"")
        # encoder_settings is 1.37+
        settings = getattr(info, "encoder_settings", u"")
        encoding = u"\n".join(filter(None, [encoder, brm, settings]))
        if encoding:
            self["~encoding"] = encoding


loader = MP3File
types = [MP3File]
