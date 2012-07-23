# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import tempfile
import base64

import mutagen

from quodlibet import config
from quodlibet import const

from quodlibet.formats._audio import AudioFile

class MutagenVCFile(AudioFile):
    format = "Unknown Mutagen + vorbiscomment"
    MutagenType = None

    def __init__(self, filename, audio=None):
        # If we're done a type probe, use the results of that to avoid
        # reopening the file.
        if audio is None:
            audio = self.MutagenType(filename)
        self["~#length"] = int(audio.info.length)
        try: self["~#bitrate"] = int(audio.info.bitrate / 1000)
        except AttributeError: pass
        for key, value in (audio.tags or {}).items():
            self[key] = "\n".join(value)
        self._post_read()
        self.sanitize(filename)

    def _post_read(self):
        email = config.get("editing", "save_email").strip()
        maps = {"rating": float, "playcount": int}
        for keyed_key, func in maps.items():
            for subkey in ["", ":" + const.EMAIL, ":" + email]:
                key = keyed_key + subkey
                if key in self:
                    try: self["~#" + keyed_key] = func(self[key])
                    except ValueError: pass
                    del(self[key])

        # only store total tracks information in totaltracks
        if "tracktotal" in self:
            self.setdefault("totaltracks", self["tracktotal"])
            del(self["tracktotal"])

        # only store total discs information in totaldiscs
        if "disctotal" in self:
            self.setdefault("totaldiscs", self["disctotal"])
            del(self["disctotal"])

        # QL expects tracknumber to include total tracks
        if "totaltracks" in self:
            if "tracknumber" in self:
                self["tracknumber"] += "/" + self["totaltracks"]
            del(self["totaltracks"])

        # QL expects discnumber to include total discs
        if "totaldiscs" in self:
            if "discnumber" in self:
                self["discnumber"] += "/" + self["totaldiscs"]
            del(self["totaldiscs"])

        if "metadata_block_picture" in self:
            self["~picture"] = "y"
            del(self["metadata_block_picture"])

        if "coverart" in self:
            self["~picture"] = "y"
            del(self["coverart"])

        if "coverartmime" in self:
            del(self["coverartmime"])

    def get_format_cover(self):
        try: from mutagen.flac import Picture
        except ImportError: return

        try: audio = self.MutagenType(self["~filename"])
        except EnvironmentError: return None

        pictures = []
        for data in audio.tags.get("metadata_block_picture", []):
            try: pictures.append(Picture(base64.b64decode(data)))
            except TypeError: pass

        cover = None
        for pic in pictures:
            if pic.type == 3:
                cover = pic.data
                break
            cover = cover or pic.data

        if not cover:
            cover = audio.tags.get("coverart")
            try: cover = cover and base64.b64decode(cover[0])
            except TypeError: cover = None

        if not cover:
            if "~picture" in self:
                del self["~picture"]
            return

        fn = tempfile.NamedTemporaryFile()
        fn.write(cover)
        fn.flush()
        fn.seek(0, 0)
        return fn

    def can_change(self, k=None):
        if k is None:
            return super(MutagenVCFile, self).can_change(None)
        else: return (super(MutagenVCFile, self).can_change(k) and
                      k not in ["rating", "playcount",
                                "metadata_block_picture",
                                "coverart", "coverartmime"] and
                      not k.startswith("rating:") and
                      not k.startswith("playcount:"))

    def _prep_write(self, comments):
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
            if rating != const.DEFAULT_RATING:
                comments["rating:" + email] = str(rating)
            playcount = self.get("~#playcount", 0)
            if playcount != 0:
                comments["playcount:" + email] = str(playcount)

    def write(self):
        audio = self.MutagenType(self["~filename"])
        if audio.tags is None:
            audio.add_tags()
        self._prep_write(audio.tags)

        split_total = {"tracknumber": "totaltracks",
                       "discnumber": "totaldiscs"}

        for key in self.realkeys():
            # Split tracknumber and save the total part as totaltracks
            # In case there is a totaltracks, ignore the second track part
            if key in split_total:
                value = self[key]
                total_key = split_total[key]
                parts = value.split("/", 1)
                audio.tags[key] = parts[0]
                if len(parts) > 1 and total_key not in self:
                    audio.tags[total_key] = parts[1]
                continue
            audio.tags[key] = self.list(key)

        audio.save()
        self.sanitize()

extensions = []
ogg_formats = []
try: from mutagen.oggvorbis import OggVorbis
except ImportError: OggVorbis = None
else:
    extensions.append(".ogg")
    extensions.append(".oga")
    ogg_formats.append(OggVorbis)

try: from mutagen.flac import FLAC, FLACNoHeaderError
except ImportError: FLAC = None
else:
    extensions.append(".flac")
    ogg_formats.append(FLAC)

try: from mutagen.oggflac import OggFLAC
except ImportError: OggFLAC = None
else:
    extensions.append(".oggflac")
    ogg_formats.append(OggFLAC)

try: from mutagen.oggspeex import OggSpeex
except ImportError: OggSpeex = None
else:
    extensions.append(".spx")
    ogg_formats.append(OggSpeex)

from mutagen.oggtheora import OggTheora
extensions.append(".ogv")
ogg_formats.append(OggTheora)

try: from mutagen.oggopus import OggOpus
except ImportError: OggOpus = None
else:
    extensions.append(".opus")
    ogg_formats.append(OggOpus)

try: from mutagen.id3 import ID3
except ImportError: ID3 = None

class OggFile(MutagenVCFile):
    format = "Ogg Vorbis"
    MutagenType = OggVorbis

class OggFLACFile(MutagenVCFile):
    format = "Ogg FLAC"
    MutagenType = OggFLAC

class OggSpeexFile(MutagenVCFile):
    format = "Ogg Speex"
    MutagenType = OggSpeex

class OggTheoraFile(MutagenVCFile):
    format = "Ogg Theora"
    MutagenType = OggTheora

class OggOpusFile(MutagenVCFile):
    format = "Ogg Opus"
    MutagenType = OggOpus

class FLACFile(MutagenVCFile):
    format = "FLAC"
    MutagenType = FLAC

    def __init__(self, filename, audio=None):
        if audio is None:
            audio = FLAC(filename)
        super(FLACFile, self).__init__(filename, audio)
        if audio.pictures:
            self["~picture"] = "y"

    def get_format_cover(self):
        try:
            tag = FLAC(self["~filename"])
        except EnvironmentError:
            return None
        else:
            covers = tag.pictures
            if not covers:
                return super(FLACFile, self).get_format_cover()

            for cover in covers:
                if cover.type == 3:
                    pic = cover
                    break
            else:
                pic = covers[0]

            fn = tempfile.NamedTemporaryFile()
            fn.write(pic.data)
            fn.flush()
            fn.seek(0, 0)
            return fn

    def write(self):
        if ID3 is not None:
            ID3().delete(filename=self["~filename"])
        super(FLACFile, self).write()

def info(filename):
    try: audio = mutagen.File(filename, options = ogg_formats)
    except AttributeError:
        audio = OggVorbis(filename)
    if audio is None and FLAC is not None:
        # FLAC with ID3
        try: audio = FLAC(filename)
        except FLACNoHeaderError: pass
    if audio is None:
        raise IOError("file type could not be determined")
    Kind = type(audio)
    for klass in globals().values():
        if Kind is getattr(klass, 'MutagenType', None):
            return klass(filename, audio)
    raise IOError("file type could not be determined")
