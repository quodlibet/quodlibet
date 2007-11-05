# Copyright 2006 Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from quodlibet.formats._audio import AudioFile

extensions = [".wma"]
try:
    import mutagen.asf
except ImportError:
    extensions = []

class WMAFile(AudioFile):
    multiple_values = False
    format = "Windows Media Audio"

    __translate = {
        "WM/AlbumTitle": "album",
        "Title": "title",
        "Author": "artist",
        "WM/AlbumArtist": "albumartist",
        "WM/Composer": "composer",
        "WM/Writer": "lyricist",
        "WM/Conductor": "conductor",
        "WM/ModifiedBy": "remixer",
        "WM/Producer": "producer",
        "WM/ContentGroupDescription": "grouping",
        "WM/SubTitle": "discsubtitle",
        "WM/TrackNumber": "tracknumber",
        "WM/PartOfSet": "discnumber",
        "WM/BeatsPerMinute": "bpm",
        "WM/Copyright": "copyright",
        "WM/ISRC": "isrc",
        "WM/Mood": "mood",
        "WM/EncodedBy": "encodedby",
        "MusicBrainz/Track Id": "musicbrainz_trackid",
        "MusicBrainz/Album Id": "musicbrainz_albumid",
        "MusicBrainz/Artist Id": "musicbrainz_artistid",
        "MusicBrainz/Album Artist Id": "musicbrainz_albumartistid",
        "MusicBrainz/TRM Id": "musicbrainz_trmid",
        "MusicIP/PUID": "musicip_puid",
        "WM/Year": "date",
    }
    __rtranslate = dict([(v, k) for k, v in __translate.iteritems()])

    def __init__(self, filename, audio=None):
        if audio is None:
            audio = mutagen.asf.ASF(filename)
        self["~#length"] = int(audio.info.length)
        self["~#bitrate"] = int(audio.info.bitrate)
        for name, values in audio.tags.items():
            try: name = self.__translate[name]
            except KeyError: continue
            self[name] = "\n".join(map(unicode, values))
        self.sanitize(filename)

    def write(self):
        audio = mutagen.asf.ASF(self["~filename"])
        for key in self.realkeys():
            try: name = self.__rtranslate[key]
            except KeyError: continue
            audio.tags[name] = self.list(key)
        audio.save()
        self.sanitize()

    def can_change(self, key=None):
        OK = self.__rtranslate.keys()
        if key is None: return super(WMAFile, self).can_change(key)
        else: return super(WMAFile, self).can_change(key) and (key in OK)

info = WMAFile
