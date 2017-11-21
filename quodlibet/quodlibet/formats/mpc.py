# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from mutagen.musepack import Musepack

from quodlibet.compat import text_type
from ._audio import translate_errors
from ._apev2 import APEv2File


class MPCFile(APEv2File):
    format = "Musepack"
    mimes = ["audio/x-musepack", "audio/x-mpc"]

    def __init__(self, filename):
        with translate_errors():
            audio = Musepack(filename)

        super(MPCFile, self).__init__(filename, audio)
        self["~#length"] = audio.info.length
        self["~#bitrate"] = int(audio.info.bitrate / 1000)
        self["~#channels"] = audio.info.channels

        version = audio.info.version
        self["~codec"] = u"%s SV%d" % (self.format, version)

        try:
            if audio.info.title_gain:
                track_g = u"%+0.2f dB" % audio.info.title_gain
                self.setdefault("replaygain_track_gain", track_g)
            if audio.info.album_gain:
                album_g = u"%+0.2f dB" % audio.info.album_gain
                self.setdefault("replaygain_album_gain", album_g)
            if audio.info.title_peak:
                track_p = text_type(audio.info.title_peak * 2)
                self.setdefault("replaygain_track_peak", track_p)
            if audio.info.album_peak:
                album_p = text_type(audio.info.album_peak * 2)
                self.setdefault("replaygain_album_peak", album_p)
        except AttributeError:
            pass

        self.sanitize(filename)

loader = MPCFile
types = [MPCFile]
extensions = [".mpc", ".mp+"]
