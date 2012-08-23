# Copyright 2005 Alexey Bobyakov <claymore.ws@gmail.com>, Joe Wreschnig
# Copyright 2006 Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import tempfile

from quodlibet import util
from quodlibet.formats._audio import AudioFile

extensions = ['.mp4', '.m4a', '.m4v']

try:
    from mutagen.mp4 import MP4
except ImportError:
    extensions = []

class MP4File(AudioFile):
    multiple_values = False
    format = "MPEG-4 AAC"
    mimes = ["audio/mp4", "audio/x-m4a", "audio/mpeg4", "audio/aac"]

    __translate = {
        "\xa9nam": "title",
        "\xa9alb": "album",
        "\xa9ART": "artist",
        "aART": "albumartist",
        "\xa9wrt": "composer",
        "\xa9day": "date",
        "\xa9cmt": "comment",
        "\xa9grp": "grouping",
        "\xa9gen": "genre",
        "tmpo": "bpm",
        "\xa9too": "encodedby",
        "cprt": "copyright",
        "soal": "albumsort",
        "soaa": "albumartistsort",
        "soar": "artistsort",
        "sonm": "titlesort",
        "soco": "composersort",
        "----:com.apple.iTunes:MusicBrainz Artist Id":
            "musicbrainz_artistid",
        "----:com.apple.iTunes:MusicBrainz Track Id": "musicbrainz_trackid",
        "----:com.apple.iTunes:MusicBrainz Album Id": "musicbrainz_albumid",
        "----:com.apple.iTunes:MusicBrainz Album Artist Id":
            "musicbrainz_albumartistid",
        "----:com.apple.iTunes:MusicIP PUID": "musicip_puid",
        "----:com.apple.iTunes:MusicBrainz Album Status":
            "musicbrainz_albumstatus",
        "----:com.apple.iTunes:MusicBrainz Album Type":
            "musicbrainz_albumtype",
        "----:com.apple.iTunes:MusicBrainz Album Release Country":
            "releasecountry",
    }
    __rtranslate = dict([(v, k) for k, v in __translate.iteritems()])

    __tupletranslate = {
        "disk": "discnumber",
        "trkn": "tracknumber",
        }
    __rtupletranslate = dict([(v, k) for k, v in __tupletranslate.iteritems()])

    def __init__(self, filename):
        audio = MP4(filename)
        self["~#length"] = int(audio.info.length)
        self["~#bitrate"] = int(audio.info.bitrate / 1000)
        for key, values in audio.items():
            if key in self.__tupletranslate:
                name = self.__tupletranslate[key]
                cur, total = values[0]
                if total:
                    self[name] = u"%d/%d" % (cur, total)
                else:
                    self[name] = unicode(cur)
            elif key in self.__translate:
                name = self.__translate[key]
                if key == "tmpo":
                    self[name] = "\n".join(map(unicode, values))
                elif key.startswith("----"):
                    self[name] = "\n".join(
                        map(lambda v: util.decode(v).strip("\x00"), values))
                else:
                    self[name] = "\n".join(values)
            elif key == "covr":
                self["~picture"] = "y"
        self.sanitize(filename)

    def write(self):
        audio = MP4(self["~filename"])
        for key in self.__translate.keys() + self.__tupletranslate.keys():
            try: del(audio[key])
            except KeyError: pass

        for key in self.realkeys():
            try: name = self.__rtranslate[key]
            except KeyError: continue
            values = self.list(key)
            if name == "tmpo":
                values = map(int, values)
            elif name.startswith("----"):
                values = map(lambda v: v.encode("utf-8"), values)
            audio[name] = values
        track, tracks = self("~#track"), self("~#tracks", 0)
        if track:
            audio["trkn"] = [(track, tracks)]
        disc, discs = self("~#disc"), self("~#discs", 0)
        if disc:
            audio["disk"] = [(disc, discs)]
        audio.save()
        self.sanitize()

    def can_change(self, key=None):
        OK = self.__rtranslate.keys() + self.__rtupletranslate.keys()
        if key is None: return OK
        else: return super(MP4File, self).can_change(key) and (key in OK)

    def get_format_cover(self):
        try:
            tag = MP4(self["~filename"])
        except (OSError, IOError):
            return None
        else:
            for cover in tag.get("covr", []):
                fn = tempfile.NamedTemporaryFile()
                fn.write(cover)
                fn.flush()
                fn.seek(0, 0)
                return fn
            else:
                return None

info = MP4File
types = [MP4File]
