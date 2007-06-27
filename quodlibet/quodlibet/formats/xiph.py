# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

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
        try: self["~#bitrate"] = int(audio.info.bitrate)
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

        if "totaltracks" in self:
            self.setdefault("tracktotal", self["totaltracks"])
            del(self["totaltracks"])

        # tracktotal is incredibly stupid; use tracknumber=x/y instead.
        if "tracktotal" in self:
            if "tracknumber" in self:
                self["tracknumber"] += "/" + self["tracktotal"]
            del(self["tracktotal"])
        if "disctotal" in self:
            if "discnumber" in self:
                self["discnumber"] += "/" + self["disctotal"]
            del(self["disctotal"])

    def can_change(self, k=None):
        if k is None:
            return super(MutagenVCFile, self).can_change(None)
        else: return (super(MutagenVCFile, self).can_change(k) and
                      k not in ["totaltracks", "tracktotal", "disctotal",
                                "rating", "playcount"] and
                      not k.startswith("rating:") and
                      not k.startswith("playcount:"))

    def _prep_write(self, comments):
        email = config.get("editing", "save_email").strip()
        for key in comments.keys():
            if key.startswith("rating:") or key.startswith("playcount:"):
                if key.split(":", 1)[1] in [const.EMAIL, email]:
                    del(comments[key])
            else: del(comments[key])

        if config.getboolean("editing", "save_to_songs"):
            email = email or const.EMAIL
            if self["~#rating"] != 0.5:
                comments["rating:" + email] = str(self["~#rating"])
            if self["~#playcount"] != 0:
                comments["playcount:" + email] = str(int(self["~#playcount"]))

    def write(self):
        audio = self.MutagenType(self["~filename"])
        if audio.tags is None:
            audio.add_tags()
        self._prep_write(audio.tags)
        for key in self.realkeys():
            audio.tags[key] = self.list(key)
        audio.save()
        self.sanitize()

extensions = []
ogg_formats = []
try: from mutagen.oggvorbis import OggVorbis
except ImportError: OggVorbis = None
else: extensions.append(".ogg")

try: from mutagen.flac import FLAC
except ImportError: FLAC = None
else: extensions.append(".flac")

try: from mutagen.oggflac import OggFLAC
except ImportError: OggFLAC = None
else: extensions.append(".oggflac")

try: from mutagen.oggspeex import OggSpeex
except ImportError: OggSpeex = None
else: extensions.append(".spx")

class OggFile(MutagenVCFile):
    format = "Ogg Vorbis"
    MutagenType = OggVorbis

class OggFLACFile(MutagenVCFile):
    format = "Ogg FLAC"
    MutagenType = OggFLAC

class OggSpeexFile(MutagenVCFile):
    format = "Ogg Speex"
    MutagenType = OggSpeex

class FLACFile(MutagenVCFile):
    format = "FLAC"
    MutagenType = FLAC

def info(filename):
    try: audio = mutagen.File(filename)
    except AttributeError:
        audio = OggVorbis(filename)
    if audio is None:
        raise IOError("file type could not be determined")
    else:
        Kind = type(audio)
        for klass in globals().values():
            if Kind is getattr(klass, 'MutagenType', None):
                return klass(filename, audio)
        else:
            raise IOError("file type could not be determined")
