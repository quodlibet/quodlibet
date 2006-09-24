# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gst

from formats._apev2 import APEv2File

extensions = [".mpc", ".mp+"]
try:
    from mutagen.musepack import Musepack
except (ImportError, OSError):
    extensions = []
else:
    if gst.registry_get_default().find_plugin("musepack") is None:
        extensions = []

class MPCFile(APEv2File):
    format = "Musepack"

    IGNORE = APEv2File.IGNORE + [
        "replaygain_track_peak", "replaygain_album_peak",
        "replaygain_track_gain", "replaygain_album_gain"]

    def __init__(self, filename):
        audio = Musepack(filename)
        super(MPCFile, self).__init__(filename, audio)
        self["~#length"] = int(audio.info.length)
        self["~#bitrate"] = int(audio.info.bitrate)

        try:
            track_g = u"%+0.2f dB" % audio.info.title_gain
            album_g = u"%+0.2f dB" % audio.info.album_gain
            track_p = unicode(audio.info.title_peak * 2)
            album_p = unicode(audio.info.album_peak * 2)
            self["replaygain_track_gain"] = track_g
            self["replaygain_track_peak"] = track_p
            self["replaygain_album_gain"] = album_g
            self["replaygain_album_peak"] = album_p
        except AttributeError:
            pass

        self.sanitize(filename)

info = MPCFile
