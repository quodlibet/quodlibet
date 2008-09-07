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
import glob
import shutil
import time

from quodlibet import const
from quodlibet import util

from quodlibet.util.uri import URI

from quodlibet.util.tags import STANDARD_TAGS as USEFUL_TAGS
from quodlibet.util.tags import MACHINE_TAGS

MIGRATE = ("~#playcount ~#laststarted ~#lastplayed ~#added "
           "~#skipcount ~#rating ~bookmark").split()
PEOPLE = ("albumartist artist author composer ~performers originalartist "
          "lyricist arranger conductor").split()

TAG_TO_SORT = {
    "artist": "artistsort",
    "album": "albumsort",
    "albumartist": "albumartistsort",
    "performersort": "performersort",
    "~performerssort": "~performerssort"
    }

SORT_TO_TAG = dict([(v, k) for (k, v) in TAG_TO_SORT.iteritems()])

PEOPLE_SORT = [TAG_TO_SORT.get(k, k) for k in PEOPLE]

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
    multiple_values = True

    format = "Unknown Audio File"

    def __sort_key(self):
        return (self("albumsort", ""),
                self.get("labelid") or self.get("musicbrainz_albumid"),
                self("~#disc", self.get("discnumber")),
                self("~#track", self.get("tracknumber")),
                self("artistsort"), self.get("musicbrainz_artistid"),
                self.get("title"),
                self.get("~filename"))
    sort_key = property(__sort_key)

    key = property(lambda self: self["~filename"])
    mountpoint = property(lambda self: self["~mountpoint"])

    def __album_key(self):
        return (self("albumsort", ""),
                self.get("album_grouping_key") or self.get("labelid") or
                self.get("musicbrainz_albumid") or "")
    album_key = property(__album_key)

    def __cmp__(self, other):
        if not other: return -1
        try: return cmp(self.sort_key, other.sort_key)
        except AttributeError: return -1

    def __hash__(self):
        # Dicts aren't hashable by default, so we need a hash
        # function. Previously this used ~filename. That created a
        # situation when an object could end up in two buckets by
        # renaming files. So now it uses identity.
        return hash(id(self))

    def __eq__(self, other):
        # And to preserve Python hash rules, we need a strict __eq__.
        return self is other

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
                return connector.join(
                    filter(None, map(self.__call__, util.tagsplit("~" + key))))
            elif key == "#track":
                try: return int(self["tracknumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key == "#disc":
                try: return int(self["discnumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key == "length":
                if self.get("~#length", 0) == 0: return default
                else: return util.format_time(self.get("~#length", 0))
            elif key == "rating":
                return util.format_rating(self.get("~#rating", 0))
            elif key == "people":
                join = "\n".join
                people = filter(None, map(self.__call__, PEOPLE))
                people = join(people).split("\n")
                index = people.index
                return join([person for (i, person) in enumerate(people)
                        if index(person) == i])
            elif key == "peoplesort":
                join = "\n".join
                people = filter(None, map(self.__call__, PEOPLE_SORT))
                people = join(people).split("\n")
                index = people.index
                return (join([person for (i, person) in enumerate(people)
                              if index(person) == i]) or
                        self("~people", default, connector))
            elif key == "performers":
                values = []
                for key in self.realkeys():
                    if key.startswith("performer:"):
                        role = key.split(":", 1)[1]
                        for value in self.list(key):
                            values.append("%s (%s)" % (value, role))
                values.extend(self.list("performer"))
                return "\n".join(values)
            elif key == "performerssort":
                values = []
                for key in self.realkeys():
                    if key.startswith("performersort:"):
                        role = key.split(":", 1)[1]
                        for value in self.list(key):
                            values.append("%s (%s)" % (value, role))
                values.extend(self.list("performersort"))
                return ("\n".join(values) or
                        self("~performers", default, connector))
            elif key == "basename":
                return os.path.basename(self["~filename"]) or self["~filename"]
            elif key == "dirname":
                return os.path.dirname(self["~filename"]) or self["~filename"]
            elif key == "uri":
                try: return self["~uri"]
                except KeyError:
                    return URI.frompath(self["~filename"])
            elif key == "format":
                return self.get("~format", self.format)
            elif key == "year":
                return self.get("date", default)[:4]
            elif key == "#year":
                try: return int(self.get("date", default)[:4])
                except (ValueError, TypeError, KeyError): return default
            elif key == "#tracks":
                try: return int(self["tracknumber"].split("/")[1])
                except (ValueError, IndexError, TypeError, KeyError):
                    return default
            elif key == "#discs":
                try: return int(self["discnumber"].split("/")[1])
                except (ValueError, IndexError, TypeError, KeyError):
                    return default
            elif key == "lyrics":
                try: fileobj = file(self.lyric_filename, "rU")
                except EnvironmentError: return default
                else: return fileobj.read().decode("utf-8", "replace")
            elif key[:1] == "#" and "~" + key not in self:
                try: return int(self[key[1:]])
                except (ValueError, TypeError, KeyError): return default
            else: return dict.get(self, "~" + key, default)

        elif key == "title":
            title = dict.get(self, "title")
            if title is None:
                basename = self("~basename")
                basename = basename.decode(const.FSCODING, "replace")
                return "%s [%s]" % (basename, _("Unknown"))
            else: return title
        elif key in SORT_TO_TAG:
            try: return self[key]
            except KeyError:
                key = SORT_TO_TAG[key]
        return dict.get(self, key, default)

    lyric_filename = property(lambda self: util.fsencode(
        os.path.join(os.path.expanduser("~/.lyrics"),
                     self.comma("artist").replace('/', '')[:128],
                     self.comma("title").replace('/', '')[:128] + '.lyric')))

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
        self.setdefault("~#rating", const.DEFAULT_RATING)
        self.setdefault("~#added", int(time.time()))

        self["~#mtime"] = util.mtime(self['~filename'])

    def to_dump(self):
        """A string of 'key=value' lines, similar to vorbiscomment output."""
        s = []
        for k in self.keys():
            if isinstance(self[k], int) or isinstance(self[k], long):
                s.append("%s=%d" % (k, self[k]))
            elif isinstance(self[k], float):
                s.append("%s=%f" % (k, self[k]))
            else:
                for v2 in self.list(k):
                    if isinstance(v2, str):
                        s.append("%s=%s" % (k, v2))
                    else:
                        s.append("%s=%s" % (k, util.encode(v2)))
        s.append("~format=%s" % self.format)
        s.append("")
        return "\n".join(s)

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
        fns = []
        # We can't pass 'base' alone to glob.glob because it probably
        # contains confusing metacharacters, and Python's glob doesn't
        # support any kind of escaping, so chdir and use relative
        # paths with known safe strings.
        try:
            olddir = os.getcwd()
            os.chdir(base)
        except EnvironmentError:
            pass
        else:
            for subdir in ["", "scan", "scans", "images", "covers"]:
                for ext in ["jpg", "jpeg", "png", "gif"]:
                    subdir = util.make_case_insensitive(subdir)
                    ext = util.make_case_insensitive(ext)
                    fns.extend(glob.glob(os.path.join(subdir, "*." + ext)))
                    fns.extend(glob.glob(os.path.join(subdir, ".*." + ext)))
            os.chdir(olddir)
        images = []
        for fn in sorted(fns):
            lfn = fn.lower()
            score = 0
            # check for the album label number
            if self.get("labelid", fn + ".").lower() in lfn: score += 100
            score += sum(map(lfn.__contains__,
                    ["front", "cover", "jacket", "folder", "albumart"]))
            if score:
                images.append((score, os.path.join(base, fn)))
        # Highest score wins.
        if images:
            try:
                return file(max(images)[1], "rb")
            except IOError:
                return None
        elif "~picture" in self:
            # Otherwise, we might have a picture stored in the metadata...
            return self.get_format_cover()
        else: return None

    def replay_gain(self, profiles):
        """Return the recommended Replay Gain scale factor.

        profiles is a list of Replay Gain profile names ('album',
        'track') to try before giving up. The special profile name
        'none' will cause no scaling to occur.
        """
        for profile in profiles:
            if profile is "none":
                return 1.0
            try:
                db = float(self["replaygain_%s_gain" % profile].split()[0])
                peak = float(self.get("replaygain_%s_peak" % profile, 1))
            except (KeyError, ValueError):
                continue
            else:
                scale = 10.**(db / 20)
                if scale * peak > 1:
                    scale = 1.0 / peak # don't clip
                return min(15, scale)
        else:
            return 1.0

    def write(self):
        """Write metadata back to the file."""
        raise NotImplementedError

    def __get_bookmarks(self):
        marks = []
        invalid = []
        for line in self.list("~bookmark"):
            try: time, mark = line.split(" ", 1)
            except: invalid.append((-1, line))
            else:
                try: time = util.parse_time(time, None)
                except: invalid.append((-1, line))
                else:
                    if time >= 0: marks.append((time, mark))
                    else: invalid.append((-1, line))
        marks.sort()
        marks.extend(invalid)
        return marks

    def __set_bookmarks(self, marks):
        result = []
        for time, mark in marks:
            if time < 0: raise ValueError("mark times must be positive")
            result.append(u"%s %s" % (util.format_time(time), mark))
        result = u"\n".join(result)
        if result: self["~bookmark"] = result
        elif "~bookmark" in self: del(self["~bookmark"])

    bookmarks = property(
        __get_bookmarks, __set_bookmarks,
        doc="""Parse and return song position bookmarks, or set them.
        Accessing this returns a copy, so song.bookmarks.append(...)
        will not work; you need to do
           marks = song.bookmarks
           marks.append(...)
           song.bookmarks = marks""")
