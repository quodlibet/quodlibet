# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.formats._apev2 import APEv2File

extensions = [".mpc", ".mp+"]
try:
    from mutagen.musepack import Musepack
except (ImportError, OSError):
    extensions = []

class MPCFile(APEv2File):
    format = "Musepack"
    mimes = ["audio/x-musepack", "audio/x-mpc"]

    def __init__(self, filename):
        audio = Musepack(filename)
        super(MPCFile, self).__init__(filename, audio)
        self["~#length"] = int(audio.info.length)
        self["~#bitrate"] = int(audio.info.bitrate / 1000)

        try:
            if audio.info.title_gain:
                track_g = u"%+0.2f dB" % audio.info.title_gain
                self.setdefault("replaygain_track_gain", track_g)
            if audio.info.album_gain:
                album_g = u"%+0.2f dB" % audio.info.album_gain
                self.setdefault("replaygain_album_gain", album_g)
            if audio.info.title_peak:
                track_p = unicode(audio.info.title_peak * 2)
                self.setdefault("replaygain_track_peak", track_p)
            if audio.info.album_peak:
                album_p = unicode(audio.info.album_peak * 2)
                self.setdefault("replaygain_album_peak", album_p)
        except AttributeError:
            pass

        self.sanitize(filename)

info = MPCFile
types = [MPCFile]
