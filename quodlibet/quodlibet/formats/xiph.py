# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys
import base64

import mutagen
from mutagen.flac import Picture

from quodlibet import config
from quodlibet import const
from quodlibet.config import RATINGS
from quodlibet.util.path import get_temp_cover_file
from quodlibet.formats._audio import AudioFile
from quodlibet.formats._image import EmbeddedImage, APICType


# Migrate old layout
sys.modules["formats.flac"] = sys.modules[__name__]
sys.modules["formats.oggvorbis"] = sys.modules[__name__]


class MutagenVCFile(AudioFile):
    format = "Unknown Mutagen + vorbiscomment"
    MutagenType = None

    can_change_images = True

    def __init__(self, filename, audio=None):
        # If we're done a type probe, use the results of that to avoid
        # reopening the file.
        if audio is None:
            audio = self.MutagenType(filename)
        self["~#length"] = int(audio.info.length)
        try:
            self["~#bitrate"] = int(audio.info.bitrate / 1000)
        except AttributeError:
            pass
        # mutagen keys are lower cased
        for key, value in (audio.tags or {}).items():
            self[key] = "\n".join(value)
        self.__post_read()
        self.sanitize(filename)

    def __post_read_total(self, main, fallback, single):
        one = None
        total = None

        if single in self:
            parts = self[single].split("/", 1)
            if parts[0]:
                one = parts[0]
            if len(parts) > 1:
                total = parts[1]
            del self[single]

        if main in self:
            total = self[main]
            del self[main]
        else:
            if fallback in self:
                total = self[fallback]
                del self[fallback]

        final = None
        if one is not None:
            final = one
        if total is not None:
            if final is None:
                final = "/" + total
            else:
                final += "/" + total

        if final is not None:
            self[single] = final

    def __post_read(self):
        email = config.get("editing", "save_email").strip()
        maps = {"rating": float, "playcount": int}
        for keyed_key, func in maps.items():
            for subkey in ["", ":" + const.EMAIL, ":" + email]:
                key = keyed_key + subkey
                if key in self:
                    try:
                        self["~#" + keyed_key] = func(self[key])
                    except ValueError:
                        pass
                    del(self[key])

        if "metadata_block_picture" in self:
            self.has_images = True
            del(self["metadata_block_picture"])

        if "coverart" in self:
            self.has_images = True
            del(self["coverart"])

        if "coverartmime" in self:
            del(self["coverartmime"])

        self.__post_read_total("tracktotal", "totaltracks", "tracknumber")
        self.__post_read_total("disctotal", "totaldiscs", "discnumber")

    def get_primary_image(self):
        """Returns the primary embedded image"""

        if not self.has_images:
            return

        try:
            audio = self.MutagenType(self["~filename"])
        except EnvironmentError:
            return None

        pictures = []
        for data in audio.get("metadata_block_picture", []):
            try:
                pictures.append(Picture(base64.b64decode(data)))
            except TypeError:
                pass

        cover = None
        for pic in pictures:
            if pic.type == APICType.COVER_FRONT:
                cover = pic
                break
            cover = cover or pic

        if cover:
            f = get_temp_cover_file(cover.data)
            return EmbeddedImage(
                f, cover.mime, cover.width, cover.height, cover.depth,
                cover.type)

        cover = audio.get("coverart")
        try:
            cover = cover and base64.b64decode(cover[0])
        except TypeError:
            cover = None

        if not cover:
            self.has_images = False
            return

        mime = audio.get("coverartmime", "image/")
        f = get_temp_cover_file(cover)
        return EmbeddedImage(f, mime)

    def clear_images(self):
        """Delete all embedded images"""

        if not self.has_images:
            return

        try:
            audio = self.MutagenType(self["~filename"])
        except EnvironmentError:
            return

        audio.pop("metadata_block_picture", None)
        audio.pop("coverart", None)
        audio.pop("coverartmime", None)
        audio.save()

        self.has_images = False

    def set_image(self, image):
        """Replaces all embedded images by the passed image"""

        try:
            audio = self.MutagenType(self["~filename"])
            data = image.file.read()
        except EnvironmentError:
            return

        pic = Picture()
        pic.data = data
        pic.type = APICType.COVER_FRONT
        pic.mime = image.mime_type
        pic.width = image.width
        pic.height = image.height
        pic.depth = image.color_depth

        audio.pop("coverart", None)
        audio.pop("coverartmime", None)
        audio["metadata_block_picture"] = base64.b64encode(pic.write())
        audio.save()

        self.has_images = True

    def can_change(self, k=None):
        if k is None:
            return super(MutagenVCFile, self).can_change(None)
        else:
            l = k.lower()
            return (super(MutagenVCFile, self).can_change(k) and
                    l not in ["rating", "playcount",
                              "metadata_block_picture",
                              "coverart", "coverartmime"] and
                    not l.startswith("rating:") and
                    not l.startswith("playcount:"))

    def __prep_write(self, comments):
        email = config.get("editing", "save_email").strip()
        for key in comments.keys():
            if key.startswith("rating:") or key.startswith("playcount:"):
                if key.split(":", 1)[1] in [const.EMAIL, email]:
                    del(comments[key])
            elif key not in ["metadata_block_picture", "coverart",
                    "coverartmime"]:
                del(comments[key])

        if config.getboolean("editing", "save_to_songs"):
            email = email or const.EMAIL
            rating = self("~#rating")
            if rating != RATINGS.default:
                comments["rating:" + email] = str(rating)
            playcount = self.get("~#playcount", 0)
            if playcount != 0:
                comments["playcount:" + email] = str(playcount)

    def __prep_write_total(self, comments, main, fallback, single):
        lower = self.as_lowercased()

        for k in [main, fallback, single]:
            if k in comments:
                del comments[k]

        if single in lower:
            parts = lower[single].split("/", 1)

            if parts[0]:
                comments[single] = [parts[0]]

            if len(parts) > 1:
                comments[main] = [parts[1]]

        if main in lower:
            comments[main] = lower.list(main)

        if fallback in lower:
            if main in comments:
                comments[fallback] = lower.list(fallback)
            else:
                comments[main] = lower.list(fallback)

    def write(self):
        audio = self.MutagenType(self["~filename"])
        if audio.tags is None:
            audio.add_tags()

        self.__prep_write(audio.tags)

        lower = self.as_lowercased()
        for key in lower.realkeys():
            audio.tags[key] = lower.list(key)

        self.__prep_write_total(audio.tags,
                                "tracktotal", "totaltracks", "tracknumber")
        self.__prep_write_total(audio.tags,
                                "disctotal", "totaldiscs", "discnumber")

        audio.save()
        self.sanitize()

extensions = []
ogg_formats = []
try:
    from mutagen.oggvorbis import OggVorbis
except ImportError:
    OggVorbis = None
else:
    extensions.append(".ogg")
    extensions.append(".oga")
    ogg_formats.append(OggVorbis)

try:
    from mutagen.flac import FLAC, FLACNoHeaderError
except ImportError:
    FLAC = None
else:
    extensions.append(".flac")
    ogg_formats.append(FLAC)

try:
    from mutagen.oggflac import OggFLAC
except ImportError:
    OggFLAC = None
else:
    extensions.append(".oggflac")
    ogg_formats.append(OggFLAC)

try:
    from mutagen.oggspeex import OggSpeex
except ImportError:
    OggSpeex = None
else:
    extensions.append(".spx")
    ogg_formats.append(OggSpeex)

from mutagen.oggtheora import OggTheora
extensions.append(".ogv")
ogg_formats.append(OggTheora)

try:
    from mutagen.oggopus import OggOpus
except ImportError:
    OggOpus = None
else:
    extensions.append(".opus")
    ogg_formats.append(OggOpus)

try:
    from mutagen.id3 import ID3
except ImportError:
    ID3 = None


class OggFile(MutagenVCFile):
    format = "Ogg Vorbis"
    mimes = ["audio/vorbis", "audio/ogg; codecs=vorbis"]
    MutagenType = OggVorbis


class OggFLACFile(MutagenVCFile):
    format = "Ogg FLAC"
    mimes = ["audio/x-oggflac", "audio/ogg; codecs=flac"]
    MutagenType = OggFLAC


class OggSpeexFile(MutagenVCFile):
    format = "Ogg Speex"
    mimes = ["audio/x-speex", "audio/ogg; codecs=speex"]
    MutagenType = OggSpeex


class OggTheoraFile(MutagenVCFile):
    format = "Ogg Theora"
    mimes = ["video/x-theora", "video/ogg; codecs=theora"]
    MutagenType = OggTheora


class OggOpusFile(MutagenVCFile):
    format = "Ogg Opus"
    mimes = ["audio/ogg; codecs=opus"]
    MutagenType = OggOpus


class FLACFile(MutagenVCFile):
    format = "FLAC"
    mimes = ["audio/x-flac", "application/x-flac"]
    MutagenType = FLAC

    def __init__(self, filename, audio=None):
        if audio is None:
            audio = FLAC(filename)
        super(FLACFile, self).__init__(filename, audio)
        if audio.pictures:
            self.has_images = True

    def get_primary_image(self):
        """Returns the primary embedded image"""

        try:
            tag = FLAC(self["~filename"])
        except EnvironmentError:
            return None

        covers = tag.pictures
        if not covers:
            return super(FLACFile, self).get_primary_image()

        covers.sort(key=lambda c: APICType.sort_key(c.type))
        cover = covers[0]

        fileobj = get_temp_cover_file(cover.data)
        return EmbeddedImage(
            fileobj, cover.mime, cover.width, cover.height, cover.depth,
            cover.type)

    def clear_images(self):
        """Delete all embedded images"""

        try:
            tag = FLAC(self["~filename"])
        except EnvironmentError:
            return

        tag.clear_pictures()
        tag.save()

        # clear vcomment tags
        super(FLACFile, self).clear_images()

        self.has_images = False

    def set_image(self, image):
        """Replaces all embedded images by the passed image"""

        try:
            tag = FLAC(self["~filename"])
            data = image.file.read()
        except EnvironmentError:
            return

        pic = Picture()
        pic.data = data
        pic.type = APICType.COVER_FRONT
        pic.mime = image.mime_type
        pic.width = image.width
        pic.height = image.height
        pic.depth = image.color_depth

        tag.add_picture(pic)
        tag.save()

        # clear vcomment tags
        super(FLACFile, self).clear_images()

        self.has_images = True

    def write(self):
        if ID3 is not None:
            ID3().delete(filename=self["~filename"])
        super(FLACFile, self).write()

types = []
for var in globals().values():
    if getattr(var, 'MutagenType', None):
        types.append(var)


def info(filename):
    try:
        audio = mutagen.File(filename, options=ogg_formats)
    except AttributeError:
        audio = OggVorbis(filename)
    if audio is None and FLAC is not None:
        # FLAC with ID3
        try:
            audio = FLAC(filename)
        except FLACNoHeaderError:
            pass
    if audio is None:
        raise IOError("file type could not be determined")
    Kind = type(audio)
    for klass in globals().values():
        if Kind is getattr(klass, 'MutagenType', None):
            return klass(filename, audio)
    raise IOError("file type could not be determined")
