# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

from formats._audio import AudioFile

DEFAULT_EMAIL = "quodlibet@lists.sacredchao.net"
EMAIL = DEFAULT_EMAIL

class VCFile(AudioFile):
    def _post_read(self):
        try: del(self["vendor"])
        except KeyError: pass

        for keyed_key in ["rating", "playcount"]:
            for subkey in ["", ":"+DEFAULT_EMAIL, ":"+EMAIL]:
                key = keyed_key + subkey
                if key in self:
                    try: self["~#"+keyed_key] = float(self[key])
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
        if k is None: return AudioFile.can_change(self, None)
        else: return (AudioFile.can_change(self, k) and
                      k not in ["vendor", "totaltracks", "tracktotal",
                                "rating", "playcount"] and
                      not k.startswith("rating:") and
                      not k.startswith("playcount:"))

    def _prep_write(self, comments):
        for key in comments.keys():
            if key.startswith("rating:") or key.startswith("playcount:"):
                if key.split(":", 1)[1] == DEFAULT_EMAIL:
                    del(comments[key])
            else: del(comments[key])
        if self["~#rating"] != 0.5:
            comments["rating:" + EMAIL] = str(self["~#rating"])
        if self["~#playcount"] != 0:
            comments["playcount:" + EMAIL] = str(self["~#playcount"])
