# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gst
from formats.audio import AudioFile

try: import ogg.vorbis
except ImportError: extensions = []
else:
    if gst.element_factory_make('vorbisdec'): extensions = [".ogg"]
    else: pass

class OggFile(AudioFile):
    def __init__(self, filename):
        import ogg.vorbis
        f = ogg.vorbis.VorbisFile(filename)
        for k, v in f.comment().as_dict().iteritems():
            if not isinstance(v, list): v = [v]
            v = u"\n".join(map(unicode, v))
            self[k.lower()] = v

        self["~#length"] = int(f.time_total(-1))
        self["~#bitrate"] = int(f.bitrate(-1))

        try: del(self["vendor"])
        except KeyError: pass

        if "rating" in self:
            try: self["~#rating"] = int(float(self["rating"]) * 4)
            except ValueError: pass
            del(self["rating"])
        if "playcount" in self:
            try: self["~#playcount"] = int(self["playcount"])
            except ValueError: pass
            del(self["playcount"])

        if "totaltracks" in self:
            self["tracktotal"].setdefault(self["totaltracks"])
            del(self["totaltracks"])

        # tracktotal is incredibly stupid; use tracknumber=x/y instead.
        if "tracktotal" in self:
            if "tracknumber" in self:
                self["tracknumber"] += "/" + self["tracktotal"]
            del(self["tracktotal"])

        self.sanitize(filename)

    def can_change(self, k=None):
        if k is None: return AudioFile.can_change(self, None)
        else: return (AudioFile.can_change(self, k) and
                      k not in ["vendor", "totaltracks", "tracktotal",
                                "rating", "playcount"])

    def write(self):
        import ogg.vorbis
        f = ogg.vorbis.VorbisFile(self['~filename'])
        comments = f.comment()
        comments.clear()
        for key in self.realkeys():
            value = self.list(key)
            for line in value: comments[key] = line
        if self["~#rating"] != 2:
            comments["rating"] = str(self["~#rating"] / 4.0)
        if self["~#playcount"] != 0:
            comments["playcount"] = str(self["~#playcount"])
        comments.write_to(self['~filename'])
        self.sanitize()

info = OggFile
