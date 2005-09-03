# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst
from formats.audio import AudioFile

try: import musepack
except ImportError: extensions = []
else:
    if gst.element_factory_make('musepackdec'): extensions = [".mpc", ".mp+"]
    else: extensions = []

class MPCFile(AudioFile):
    # Map APE names to QL names. APE tags are also usually capitalized.
    # Also blacklist a number of tags.
    IGNORE = ["file", "index", "introplay", "dummy",
              "replaygain_track_peak", "replaygain_album_peak",
              "replaygain_track_gain", "replaygain_album_gain"]
    TRANS = { "subtitle": "version",
              "track": "tracknumber",
              "catalog": "labelid",
              "record date": "date",
              "record location": "location"
              }
    SNART = dict([(v, k) for k, v in TRANS.iteritems()])
    
    def __init__(self, filename):
        tag = musepack.APETag(filename)
        for key, value in tag:
            key = MPCFile.TRANS.get(key.lower(), key.lower())
            if (value.kind == musepack.apev2.TEXT and
                key not in MPCFile.IGNORE):
                self[key] = "\n".join(list(value))
        f = musepack.MPCFile(filename)
        self["~#length"] = int(f.length / 1000)
        try: self["~#bitrate"] = int(f.bitrate)
        except AttributeError: pass
        try:
            track_g = "%+0.2f dB" % (f.gain_radio / 100.0)
            album_g = "%+0.2f dB" % (f.gain_audiophile / 100.0)
            track_p = str(f.peak_radio / 32767.0)
            album_p = str(f.peak_audiophile / 32767.0)
        except AttributeError: pass
        else:
            self["replaygain_track_gain"] = track_g
            self["replaygain_track_peak"] = track_p
            self["replaygain_album_gain"] = album_g
            self["replaygain_album_peak"] = album_p

        self.sanitize(filename)

    def can_change(self, key = None):
        if key is None: return True
        else: return (AudioFile.can_change(self, key) and
                      key not in MPCFile.IGNORE)

    def write(self):
        import musepack
        tag = musepack.APETag(self['~filename'])

        keys = tag.keys()
        for key in keys:
            # remove any text keys we read in
            value = tag[key]
            if (value.kind == musepack.apev2.TEXT and
                key not in MPCFile.IGNORE):
                del(tag[key])
        for key in self.realkeys():
            value = self[key]
            key = MPCFile.SNART.get(key, key)
            if key in ["isrc", "isbn", "ean/upc"]: key = key.upper()
            else: key = key.title()
            tag[key] = value.split("\n")
        tag.write()
        self.sanitize()

info = MPCFile
