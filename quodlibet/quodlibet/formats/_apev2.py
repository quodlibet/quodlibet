# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from quodlibet.formats._audio import AudioFile

try: import mutagen.apev2
except ImportError: pass

class APEv2File(AudioFile):
    # Map APE names to QL names. APE tags are also usually capitalized.
    # Also blacklist a number of tags.
    IGNORE = ["file", "index", "introplay", "dummy"]
    TRANS = { "subtitle": "version",
              "track": "tracknumber",
              "catalog": "labelid",
              "year": "date",
              "record location": "location",
              "album artist": "albumartist",
              "debut album": "originalalbum",
              "record date": "recordingdate",
              "original artist": "originalartist",
              "mixartist": "remixer",
              }
    SNART = dict([(v, k) for k, v in TRANS.iteritems()])

    def __init__(self, filename, audio=None):
        if audio:
            tag = audio.tags or {}
        else:
            try: tag = mutagen.apev2.APEv2(filename)
            except mutagen.apev2.APENoHeaderError: tag = {}
        for key, value in tag.items():
            key = self.TRANS.get(key.lower(), key.lower())
            if (value.kind == mutagen.apev2.TEXT and
                key not in self.IGNORE):
                self[key] = "\n".join(list(value))

    def can_change(self, key=None):
        if key is None: return True
        else: return (super(APEv2File, self).can_change(key) and
                      key not in self.IGNORE and key not in self.TRANS)

    def write(self):
        try: tag = mutagen.apev2.APEv2(self['~filename'])
        except mutagen.apev2.APENoHeaderError:
            tag = mutagen.apev2.APEv2()

        keys = tag.keys()
        for key in keys:
            # remove any text keys we read in
            value = tag[key]
            if (value.kind == mutagen.apev2.TEXT and key not in self.IGNORE):
                del(tag[key])
        for key in self.realkeys():
            if key in self.IGNORE: continue
            value = self[key]
            key = self.SNART.get(key, key)
            if key in ["isrc", "isbn", "ean/upc"]: key = key.upper()
            else: key = key.title()
            tag[key] = value.split("\n")
        tag.save(self["~filename"])
        self.sanitize()
