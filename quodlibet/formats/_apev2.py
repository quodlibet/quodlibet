# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from formats._audio import AudioFile
try: import musepack.apev2
except ImportError: pass

class APEv2File(AudioFile):
    # Map APE names to QL names. APE tags are also usually capitalized.
    # Also blacklist a number of tags.
    IGNORE = ["file", "index", "introplay", "dummy",
              "replaygain_track_peak", "replaygain_album_peak",
              "replaygain_track_gain", "replaygain_album_gain"]
    TRANS = { "subtitle": "version",
              "track": "tracknumber",
              "catalog": "labelid",
              "record location": "location"
              }
    SNART = dict([(v, k) for k, v in TRANS.iteritems()])

    def __init__(self, filename):
        tag = musepack.apev2.APETag(filename)
        for key, value in tag:
            key = self.TRANS.get(key.lower(), key.lower())
            if (value.kind == musepack.apev2.TEXT and
                key not in self.IGNORE):
                self[key] = "\n".join(list(value))
    def can_change(self, key=None):
        if key is None: return True
        else: return (AudioFile.can_change(self, key) and
                      key not in self.IGNORE)

    def write(self):
        import musepack.apev2
        tag = musepack.apev2.APETag(self['~filename'])

        keys = tag.keys()
        for key in keys:
            # remove any text keys we read in
            value = tag[key]
            if (value.kind == musepack.apev2.TEXT and key not in self.IGNORE):
                del(tag[key])
        for key in self.realkeys():
            if key in self.IGNORE: continue
            value = self[key]
            key = self.SNART.get(key, key)
            if key in ["isrc", "isbn", "ean/upc"]: key = key.upper()
            else: key = key.title()
            tag[key] = value.split("\n")
        tag.write()
        self.sanitize()

