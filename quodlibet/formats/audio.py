# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import gettext
import shutil
import time

import util, config

class Unknown(unicode): pass

if sys.version_info < (2, 4): from sets import Set as set

MIGRATE = ["~#playcount", "~#lastplayed", "~#added", "~#skipcount", "~#rating"]

# Tags to display in the "Add Tag" dialogs
USEFUL_TAGS = (
    # Ogg Vorbis spec tags
    "title version album tracknumber artist genre performer copyright "
    "license organization description location contact isrc "

    # Other tags we like
    "arranger author composer conductor lyricist discnumber labelid part "
    "website language bpm"
    ).split()

class AudioFile(dict):
    def __cmp__(self, other):
        if not other: return -1
        return (cmp(self("album"), other("album")) or
                cmp(self("~#disc"), other("~#disc")) or
                cmp(self("~#track"), other("~#track")) or
                cmp(self("artist"), other("artist")) or
                cmp(self("title"), other("title")) or
                cmp(self("~filename"), other("~filename")))

    def reload(self):
        fn = self["~filename"]
        saved = {}
        for key in self:
            if key in MIGRATE or key.startswith("~#playlist_"):
                saved[key] = self[key]
        self.clear()
        self["~filename"] = fn
        self.__init__(fn)
        self.update(saved)

    def realkeys(self):
        return filter(lambda s: s and s[0] != "~", self.keys())

    def __call__(self, key, default=""):
        if key and key[0] == "~":
            key = key[1:]
            if "~" in key:
                parts = [self(p) for p in key.split("~")]
                return " - ".join(filter(None, parts))
            elif key == "basename": return os.path.basename(self["~filename"])
            elif key == "dirname": return os.path.dirname(self["~filename"])
            elif key == "length":
                return util.format_time(self.get("~#length", 0))
            elif key == "rating":
                return util.format_rating(self.get("~#rating", 0))
            elif key == "#track":
                try: return int(self["tracknumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key == "#disc":
                try: return int(self["discnumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key[0] == "#" and "~" + key not in self:
                try: return int(self[key[1:]])
                except (ValueError, TypeError, KeyError): return default
            else: return dict.get(self, "~" + key, default)
        elif key == "title":
            v = dict.get(self, "title")
            if v is None:
                return "%s [%s]" %(
                    os.path.basename(self["~filename"]).decode(
                    util.fscoding(), "replace"), Unknown(_("Unknown")))
            else: return v
        elif (key == "artist" or key == "album"):
            return self.get(key, Unknown(_("Unknown")))
        else: return dict.get(self, key, default)

    def comma(self, key):
        v = self(key, "")
        if isinstance(v, int): return v
        else: return v.replace("\n", ", ")

    def list(self, key):
        try: return self[key].split("\n")
        except (KeyError, AttributeError): return []

    def listall(self, *keys):
        return reduce(set.union, map(self.list, keys), set())

    def exists(self):
        return os.path.exists(self["~filename"])

    def valid(self):
        return (self.exists() and
                self["~#mtime"] == util.mtime(self["~filename"]))

    def mounted(self):
        return os.path.ismount(self.get("~mountpoint", "/"))

    def can_change(self, k=None):
        if k is None:
            if os.access(self["~filename"], os.W_OK): return True
            else: return []
        else: return (k and k != "vendor" and "=" not in k and "~" not in k
                      and os.access(self["~filename"], os.W_OK))

    def rename(self, newname):
        if newname[0] == os.sep: util.mkdir(os.path.dirname(newname))
        else: newname = os.path.join(self('~dirname'), newname)
        if not os.path.exists(newname):
            shutil.move(self['~filename'], newname)
        elif newname != self['~filename']: raise ValueError
        self.sanitize(newname)

    def website(self):
        if "website" in self: return self.list("website")[0]
        for cont in self.list("contact") + self.list("comment"):
            c = cont.lower()
            if (c.startswith("http://") or c.startswith("https://") or
                c.startswith("www.")): return cont
            elif c.startswith("//www."): return "http:" + cont
        else:
            text = "http://www.google.com/search?q="
            esc = lambda c: ord(c) > 127 and '%%%x'%ord(c) or c
            if "labelid" in self: text += ''.join(map(esc, self["labelid"]))
            else:
                artist = util.escape("+".join(self("artist").split()))
                album = util.escape("+".join(self("album").split()))
                artist = util.encode(artist)
                album = util.encode(album)
                artist = "%22" + ''.join(map(esc, artist)) + "%22"
                album = "%22" + ''.join(map(esc, album)) + "%22"
                text += artist + "+" + album
            text += "&ie=UTF8"
            return text

    # Sanity-check all sorts of things...
    def sanitize(self, filename=None):
        if filename: self["~filename"] = filename
        elif "~filename" not in self: raise ValueError("Unknown filename!")

        # Fill in necessary values.
        self.setdefault("~#lastplayed", 0)
        self.setdefault("~#playcount", 0)
        self.setdefault("~#skipcount", 0)
        self.setdefault("~#length", 0)
        self.setdefault("~#bitrate", 0)
        self.setdefault("~#rating", 2)
        self.setdefault("~#added", int(time.time()))

        # Clean up Vorbis garbage.
        try: del(self["vendor"])
        except KeyError: pass

        self["~#mtime"] = util.mtime(self['~filename'])

        # Find mount point (terminating at "/" if necessary)
        head = self["~filename"]
        while "~mountpoint" not in self:
            head, tail = os.path.split(head)
            # Prevent infinite loop without a fully-qualified filename
            # (the unit tests use these).
            head = head or "/"
            if os.path.ismount(head):
                self["~mountpoint"] = head

    # key=value list, for ~/.quodlibet/current interface
    def to_dump(self):
        s = ""
        for k in self.keys():
            if isinstance(self[k], int):
                s += "%s=%d\n" % (k, self[k])
            else:
                for v2 in self.list(k):
                    if isinstance(v2, str):
                        s += "%s=%s\n" % (k, v2)
                    else:
                        s += "%s=%s\n" % (k, util.encode(v2))
        return s

    # Try to change a value in the data to a new value; if the
    # value being changed from doesn't exist, just overwrite the
    # whole value.
    def change(self, key, old_value, new_value):
        try:
            parts = self.list(key)
            try: parts[parts.index(old_value)] = new_value
            except ValueError:
                self[key] = new_value
            else:
                self[key] = "\n".join(parts)
        except KeyError: self[key] = new_value

    def add(self, key, value):
        if key not in self: self[key] = value
        else: self[key] += "\n" + value

    # Like change, if the value isn't found, remove all values...
    def remove(self, key, value):
        if key not in self: return
        elif self[key] == value: del(self[key])
        else:
            try:
                parts = self.list(key)
                parts.remove(value)
                self[key] = "\n".join(parts)
            except ValueError:
                if key in self: del(self[key])

    # Try to find an album cover for the file
    def find_cover(self):
        base = self('~dirname')
        try: fns = os.listdir(base)
        except EnvironmentError:  return None
        images = []
        fns.sort()
        for fn in fns:
            lfn = fn.lower()
            if lfn[-4:] in ["jpeg", ".jpg", ".png", ".gif"]:
                score = 0
                # check for the album label number
                if self.get("labelid", lfn + ".").lower() in lfn: score += 100
                matches = filter(lambda s: s in lfn,
                                 ["front", "cover", "jacket", "folder"])
                score += len(matches)
                if score: images.append((score, os.path.join(base, fn)))
        # Highest score wins.
        if images: return file(max(images)[1], "rb")
        elif "~picture" in self:
            # Otherwise, we might have a picture stored in the metadata...
            return self.get_format_cover()
        else: return None

class AudioPlayer(object):
    def __init__(self):
        self.stopped = False

    def end(self):
        self.stopped = True

    def replay_gain(self, song):
        gain = config.getint("settings", "gain")
        try:
            if gain == 0: raise ValueError
            elif gain == 2 and "replaygain_album_gain" in song:
                db = float(song["replaygain_album_gain"].split()[0])
                peak = float(song["replaygain_album_peak"])
            elif gain > 0 and "replaygain_track_gain" in song:
                db = float(song["replaygain_track_gain"].split()[0])
                peak = float(song["replaygain_track_peak"])
            else: raise ValueError
            self.scale = 10.**(db / 20)
            if self.scale * peak > 1: self.scale = 1.0 / peak # don't clip
            if self.scale > 15: self.scale = 15 # probably messed up...
        except (KeyError, ValueError):
            self.scale = 1

