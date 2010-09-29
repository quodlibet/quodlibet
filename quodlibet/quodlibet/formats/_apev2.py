# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

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

        self.sanitize(filename)

    @staticmethod
    def __titlecase(key):
        if key.lower() in ["isrc", "isbn", "ean/upc"]: return key.upper()
        else: return key.title()

    def can_change(self, key=None):
        if key is None: return True
        else: return (super(APEv2File, self).can_change(key) and
                      key.lower() not in self.IGNORE and
                      key.lower() not in self.TRANS and
                      mutagen.apev2.is_valid_apev2_key(self.__titlecase(key)))

    def write(self):
        try: tag = mutagen.apev2.APEv2(self['~filename'])
        except mutagen.apev2.APENoHeaderError:
            tag = mutagen.apev2.APEv2()

        # Remove any text keys we read in
        for key in tag.iterkeys():
            value = tag[key]
            if (value.kind == mutagen.apev2.TEXT and
                key.lower() not in self.IGNORE):
                del(tag[key])

        # Merge all case differing keys together and titlecase them
        for key in self.realkeys():
            value = self[key]
            key = self.SNART.get(key.lower(), key.lower())
            if key in self.IGNORE: continue
            key = self.__titlecase(key)
            if key in tag:
                old_val = tag[key]
                if old_val.kind == mutagen.apev2.TEXT:
                    tag[key] = list(old_val) + value.split("\n")
                else: # FIXME: We overwrite data here.
                    tag[key] = value.split("\n")
            else:
                tag[key] = value.split("\n")

        tag.save(self["~filename"])
        self.sanitize()
