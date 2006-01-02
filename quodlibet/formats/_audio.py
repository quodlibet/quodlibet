# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Much of this code is highly optimized, because many of the functions
# are called in tight loops. Don't change things just to make them
# more readable, unless they're also faster.

import os
import shutil
import time

import util, config

from urllib import pathname2url
def to_uri(filename): return "file://" + pathname2url(filename)

MIGRATE = ("~#playcount ~#laststarted ~#lastplayed ~#added "
           "~#skipcount ~#rating").split()
PEOPLE = "artist author composer performer lyricist arranger conductor".split()

class AudioFile(dict):
    """An audio file. It looks like a dict, but implements synthetic
    and tied tags via __call__ rather than __getitem__. This means
    __getitem__, get, and so on can be used for efficiency.

    If you need to sort many AudioFiles, you can use their sort_key
    attribute as a decoration."""

    fill_metadata = False
    multisong = False
    can_add = True
    is_file = True

    format = "Unknown Audio File"

    def __sort_key(self):
        return (self.get("album"), self.get("labelid"),
                self("~#disc"), self("~#track"),
                self.get("artist"), self.get("title"),
                self.get("~filename"))
    sort_key = property(__sort_key)

    def __cmp__(self, other):
        if not other: return -1
        try: return cmp(self.sort_key, other.sort_key)
        except AttributeError: return -1

    def __eq__(self, other):
        """AudioFiles are equal if they have the same filename."""

        try: return self.get("~filename") == other.get("~filename")
        except: return False

    def reload(self):
        """Reload an audio file from disk. The caller is responsible for
        handling any errors."""

        fn = self["~filename"]
        saved = {}
        for key in self:
            if key in MIGRATE: saved[key] = self[key]
        self.clear()
        self["~filename"] = fn
        self.__init__(fn)
        self.update(saved)

    def __hash__(self):
        return hash(self["~filename"])

    def realkeys(self):
        """Returns a list of keys that are not internal, i.e. they don't
        have '~' in them."""

        return filter(lambda s: s[:1] != "~", self.keys())

    def __call__(self, key, default=u"", connector=" - "):
        """Return a key, synthesizing it if necessary. A default value
        may be given (like dict.get); the default default is an empty
        unicode string (even if the tag is numeric).

        If a tied tag ('a~b') is requested, the 'connector' keyword
        argument may be used to specify what it is tied with.

        For details on tied tags, see the documentation for util.tagsplit."""

        if key[:1] == "~":
            key = key[1:]
            if "~" in key:
                parts = filter(None, map(self.__call__, util.tagsplit(key)))
                return connector.join(parts)
            elif key == "basename": return os.path.basename(self["~filename"])
            elif key == "dirname": return os.path.dirname(self["~filename"])
            elif key == "length":
                if self.get("~#length", 0) == 0: return default
                else: return util.format_time(self.get("~#length", 0))
            elif key == "rating":
                return util.format_rating(self.get("~#rating", 0))
            elif key == "#track":
                try: return int(self["tracknumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key == "#disc":
                try: return int(self["discnumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key == "people":
                join = "\n".join
                people = filter(None, map(self.get, PEOPLE))
                people = join(people).split("\n")
                index = people.index
                return join([person for (i,person) in enumerate(people)
                        if index(person)==i])
            elif key == "uri":
                try: return self["~uri"]
                except KeyError: return to_uri(self["~filename"])
            elif key == "format":
                return self.format
            elif key == "year":
                return self.get("date", default)[:4]
            elif key == "#year":
                try: return int(self.get("date", default)[:4])
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
                    util.fscoding, "replace"), _("Unknown"))
            else: return v
        else: return dict.get(self, key, default)

    def comma(self, key):
        """Get all values of a tag, separated by commas. Synthetic
        tags are supported, but will be slower. If the value is
        numeric, that is returned rather than a list."""

        if "~" in key or key == "title": v = self(key, u"")
        else: v = self.get(key, u"")
        if isinstance(v, int): return v
        elif isinstance(v, float): return v
        else: return v.replace("\n", ", ")

    def list(self, key):
        """Get all values of a tag, as a list. Synthetic tags are supported,
        but will be slower. Numeric tags are not supported.

        An empty synthetic tag cannot be distinguished from a non-existent
        synthetic tag; both result in []."""

        if "~" in key or key == "title":
            v = self(key, connector="\n")
            if v == "": return []
            else: return v.split("\n")
        elif key in self: return self[key].split("\n")
        else: return []

    def exists(self):
        """Return true if the file still exists (or we can't tell)."""

        return os.path.exists(self["~filename"])

    def valid(self):
        """Return true if the file cache is up-to-date (checked via
        mtime), or we can't tell."""
        return (self.get("~#mtime", 0) and
                self["~#mtime"] == util.mtime(self["~filename"]))

    def mounted(self):
        """Return true if the disk the file is on is mounted, or
        the file is not on a disk."""
        return os.path.ismount(self.get("~mountpoint", "/"))

    def can_change(self, k=None):
        """See if this file supports changing the given tag. This may
        be a limitation of the file type, or the file may not be
        writable.

        If no arguments are given, return a list of tags that can be
        changed, or True if 'any' tags can be changed (specific tags
        should be checked before adding)."""

        if k is None:
            if os.access(self["~filename"], os.W_OK): return True
            else: return []
        else: return (k and "=" not in k and "~" not in k
                      and os.access(self["~filename"], os.W_OK))

    def rename(self, newname):
        """Rename a file. Errors are not handled. This shouldn't be used
        directly; use library.rename instead."""

        if newname[0] == os.sep: util.mkdir(os.path.dirname(newname))
        else: newname = os.path.join(self('~dirname'), newname)
        if not os.path.exists(newname):
            shutil.move(self['~filename'], newname)
        elif newname != self['~filename']: raise ValueError
        self.sanitize(newname)

    def website(self):
        """Look for a URL in the audio metadata, or a Google search
        if no URL can be found."""

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

    def sanitize(self, filename=None):
        """Fill in metadata defaults. Find ~mountpoint, ~#mtime,
        and ~#added."""

        if filename: self["~filename"] = filename
        elif "~filename" not in self: raise ValueError("Unknown filename!")
        if self.is_file:
            self["~filename"] = os.path.realpath(self["~filename"])
            # Find mount point (terminating at "/" if necessary)
            head = self["~filename"]
            while "~mountpoint" not in self:
                head, tail = os.path.split(head)
                # Prevent infinite loop without a fully-qualified filename
                # (the unit tests use these).
                head = head or "/"
                if os.path.ismount(head): self["~mountpoint"] = head
        else: self["~mountpoint"] = "/"

        # Fill in necessary values.
        self.setdefault("~#lastplayed", 0)
        self.setdefault("~#laststarted", 0)
        self.setdefault("~#playcount", 0)
        self.setdefault("~#skipcount", 0)
        self.setdefault("~#length", 0)
        self.setdefault("~#bitrate", 0)
        self.setdefault("~#rating", 0.5)
        self.setdefault("~#added", int(time.time()))

        self["~#mtime"] = util.mtime(self['~filename'])

    def to_dump(self):
        """A string of 'key=value' lines, similar to vorbiscomment output."""
        s = ""
        for k in self.keys():
            if isinstance(self[k], int) or isinstance(self[k], long):
                s += "%s=%d\n" % (k, self[k])
            elif isinstance(self[k], float):
                s += "%s=%f\n" % (k, self[k])
            else:
                for v2 in self.list(k):
                    if isinstance(v2, str):
                        s += "%s=%s\n" % (k, v2)
                    else:
                        s += "%s=%s\n" % (k, util.encode(v2))
        return s

    def change(self, key, old_value, new_value):
        """Change 'old_value' to 'new_value' for the given metadata key.
        If the old value is not found, set the key to the new value."""
        try:
            parts = self.list(key)
            try: parts[parts.index(old_value)] = new_value
            except ValueError:
                self[key] = new_value
            else:
                self[key] = "\n".join(parts)
        except KeyError: self[key] = new_value

    def add(self, key, value):
        """Add a value for the given metadata key."""
        if key not in self: self[key] = value
        else: self[key] += "\n" + value

    def remove(self, key, value):
        """Remove a value from the given key; if the value is not found,
        remove all values for that key."""
        if key not in self: return
        elif self[key] == value: del(self[key])
        else:
            try:
                parts = self.list(key)
                parts.remove(value)
                self[key] = "\n".join(parts)
            except ValueError:
                if key in self: del(self[key])

    def find_cover(self):
        """Return a file-like containing cover image data, or None if
        no cover is available."""

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

    def replay_gain(self):
        """Return the recommended ReplayGain scale factor as a floating
        point number, based on the current settings."""

        gain = config.getint("settings", "gain")
        try:
            if gain == 0: raise ValueError
            elif gain == 2 and "replaygain_album_gain" in self:
                db = float(self["replaygain_album_gain"].split()[0])
                peak = float(self["replaygain_album_peak"])
            elif gain > 0 and "replaygain_track_gain" in self:
                db = float(self["replaygain_track_gain"].split()[0])
                peak = float(self["replaygain_track_peak"])
            else: raise ValueError
            scale = 10.**(db / 20)
            if scale * peak > 1: scale = 1.0 / peak # don't clip
            return min(15, scale)
        except (KeyError, ValueError):
            return 1

    def write(self):
        """Write metadata back to the file."""
        raise NotImplementedError
