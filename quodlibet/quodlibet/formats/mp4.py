# -*- coding: utf-8 -*-
# Copyright 2005 Alexey Bobyakov <claymore.ws@gmail.com>, Joe Wreschnig
# Copyright 2006 Lukas Lalinsky
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from mutagen.mp4 import MP4, MP4Cover

from quodlibet.util.path import get_temp_cover_file
from quodlibet.util.string import decode
from quodlibet.compat import iteritems, listkeys, text_type

from ._audio import AudioFile
from ._misc import AudioFileError, translate_errors
from ._image import EmbeddedImage


class MP4File(AudioFile):
    format = "MPEG-4"
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
        "\xa9too": "encodedby",  # FIXME: \xa9enc should be encodedby
        "cprt": "copyright",
        "soal": "albumsort",
        "soaa": "albumartistsort",
        "soar": "artistsort",
        "sonm": "titlesort",
        "soco": "composersort",

        "----:com.apple.iTunes:CONDUCTOR": "conductor",
        "----:com.apple.iTunes:DISCSUBTITLE": "discsubtitle",
        "----:com.apple.iTunes:LANGUAGE": "language",
        "----:com.apple.iTunes:MOOD": "mood",

        "----:com.apple.iTunes:MusicBrainz Artist Id":
            "musicbrainz_artistid",
        "----:com.apple.iTunes:MusicBrainz Track Id": "musicbrainz_trackid",
        "----:com.apple.iTunes:MusicBrainz Release Track Id":
            "musicbrainz_releasetrackid",
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
        '----:com.apple.iTunes:MusicBrainz Release Group Id':
            'musicbrainz_releasegroupid',

        '----:com.apple.iTunes:replaygain_album_gain': 'replaygain_album_gain',
        '----:com.apple.iTunes:replaygain_album_peak': 'replaygain_album_peak',
        '----:com.apple.iTunes:replaygain_track_gain': 'replaygain_track_gain',
        '----:com.apple.iTunes:replaygain_track_peak': 'replaygain_track_peak',
        '----:com.apple.iTunes:replaygain_reference_loudness':
            'replaygain_reference_loudness',
    }
    __rtranslate = dict([(v, k) for k, v in iteritems(__translate)])

    __tupletranslate = {
        "disk": "discnumber",
        "trkn": "tracknumber",
        }
    __rtupletranslate = dict([(v, k) for k, v in iteritems(__tupletranslate)])

    def __init__(self, filename):
        with translate_errors():
            audio = MP4(filename)
        self["~codec"] = audio.info.codec_description
        self["~#length"] = audio.info.length
        self["~#bitrate"] = int(audio.info.bitrate / 1000)
        if audio.info.channels:
            self["~#channels"] = audio.info.channels
        self["~#samplerate"] = audio.info.sample_rate

        for key, values in audio.items():
            if key in self.__tupletranslate:
                if values:
                    name = self.__tupletranslate[key]
                    cur, total = values[0]
                    if total:
                        self[name] = u"%d/%d" % (cur, total)
                    else:
                        self[name] = text_type(cur)
            elif key in self.__translate:
                name = self.__translate[key]
                if key == "tmpo":
                    self[name] = u"\n".join(map(text_type, values))
                elif key.startswith("----"):
                    self[name] = "\n".join(
                        map(lambda v: decode(v).strip("\x00"), values))
                else:
                    self[name] = "\n".join(values)
            elif key == "covr":
                self.has_images = True
        self.sanitize(filename)

    def write(self):
        with translate_errors():
            audio = MP4(self["~filename"])

        for key in (listkeys(self.__translate) +
                    listkeys(self.__tupletranslate)):
            try:
                del(audio[key])
            except KeyError:
                pass

        for key in self.realkeys():
            try:
                name = self.__rtranslate[key]
            except KeyError:
                continue
            values = self.list(key)
            if name == "tmpo":
                values = list(map(lambda v: int(round(float(v))), values))
            elif name.startswith("----"):
                values = list(map(lambda v: v.encode("utf-8"), values))
            audio[name] = values
        track, tracks = self("~#track"), self("~#tracks", 0)
        if track:
            audio["trkn"] = [(track, tracks)]
        disc, discs = self("~#disc"), self("~#discs", 0)
        if disc:
            audio["disk"] = [(disc, discs)]
        with translate_errors():
            audio.save()
        self.sanitize()

    def can_multiple_values(self, key=None):
        if key is None:
            return []
        return False

    def can_change(self, key=None):
        OK = listkeys(self.__rtranslate) + listkeys(self.__rtupletranslate)
        if key is None:
            return OK
        else:
            return super(MP4File, self).can_change(key) and (key in OK)

    def get_images(self):
        images = []

        try:
            tag = MP4(self["~filename"])
        except Exception:
            return []

        for cover in tag.get("covr", []):

            if cover.imageformat == MP4Cover.FORMAT_JPEG:
                mime = "image/jpeg"
            elif cover.imageformat == MP4Cover.FORMAT_PNG:
                mime = "image/png"
            else:
                mime = "image/"

            f = get_temp_cover_file(cover)
            images.append(EmbeddedImage(f, mime))

        return images

    def get_primary_image(self):
        try:
            tag = MP4(self["~filename"])
        except Exception:
            return

        for cover in tag.get("covr", []):

            if cover.imageformat == MP4Cover.FORMAT_JPEG:
                mime = "image/jpeg"
            elif cover.imageformat == MP4Cover.FORMAT_PNG:
                mime = "image/png"
            else:
                mime = "image/"

            f = get_temp_cover_file(cover)
            return EmbeddedImage(f, mime)

    can_change_images = True

    def clear_images(self):
        """Delete all embedded images"""

        with translate_errors():
            tag = MP4(self["~filename"])
            tag.pop("covr", None)
            tag.save()

        self.has_images = False

    def set_image(self, image):
        """Replaces all embedded images by the passed image"""

        if image.mime_type == "image/jpeg":
            image_format = MP4Cover.FORMAT_JPEG
        elif image.mime_type == "image/png":
            image_format = MP4Cover.FORMAT_PNG
        else:
            raise AudioFileError(
                "mp4: Unsupported image format %r" % image.mime_type)

        with translate_errors():
            tag = MP4(self["~filename"])

        try:
            data = image.read()
        except EnvironmentError:
            return

        cover = MP4Cover(data, image_format)
        tag["covr"] = [cover]

        with translate_errors():
            tag.save()

        self.has_images = True

loader = MP4File
types = [MP4File]
extensions = ['.mp4', '.m4a', '.m4v', '.3gp', '.3g2', '.3gp2']
