# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from formats._audio import AudioFile

class VCFile(AudioFile):
    def sanitize(self, *args, **kwargs):
        try: del(self["vendor"])
        except KeyError: pass

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

        AudioFile.sanitize(self, *args, **kwargs)

    def can_change(self, k=None):
        if k is None: return AudioFile.can_change(self, None)
        else: return (AudioFile.can_change(self, k) and
                      k not in ["vendor", "totaltracks", "tracktotal",
                                "rating", "playcount"])

    def _prep_write(self, comments):
        if self["~#rating"] != 2:
            comments["rating"] = str(self["~#rating"] / 4.0)
        if self["~#playcount"] != 0:
            comments["playcount"] = str(self["~#playcount"])
        
