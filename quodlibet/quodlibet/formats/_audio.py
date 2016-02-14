# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#           2012-2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Much of this code is highly optimized, because many of the functions
# are called in tight loops. Don't change things just to make them
# more readable, unless they're also faster.

import os
import shutil
import time

from quodlibet import util
from quodlibet import config
from quodlibet.util.path import mkdir, fsdecode, mtime, expanduser, is_fsnative
from quodlibet.util.path import normalize_path, fsnative, escape_filename
from quodlibet.util.string import encode, decode, isascii

from quodlibet.util import iso639
from quodlibet.util.uri import URI
from quodlibet.util import human_sort_key as human, capitalize

from quodlibet.util.tags import TAG_ROLES, TAG_TO_SORT
from quodlibet.compat import iteritems, string_types, text_type, number_types

from ._image import ImageContainer

try:
    from itertools import izip_longest
except ImportError:  # python3.x
    izip = zip

MIGRATE = {"~#playcount", "~#laststarted", "~#lastplayed", "~#added",
           "~#skipcount", "~#rating", "~bookmark"}
"""These get migrated if a song gets reloaded"""

PEOPLE = ["artist", "albumartist", "author", "composer", "~performers",
          "originalartist", "lyricist", "arranger", "conductor"]
"""Sources of the ~people tag, most important first"""

INTERN_NUM_DEFAULT = {"~#lastplayed", "~#laststarted", "~#playcount",
                      "~#skipcount", "~#length", "~#bitrate", "~#filesize"}
"""Default to 0"""

FILESYSTEM_TAGS = {"~filename", "~basename", "~dirname"}
"""Values are bytes in Linux instead of unicode"""

SORT_TO_TAG = dict([(v, k) for (k, v) in iteritems(TAG_TO_SORT)])
"""Reverse map, so sort tags can fall back to the normal ones"""

PEOPLE_SORT = [TAG_TO_SORT.get(k, k) for k in PEOPLE]
"""Sources for ~peoplesort, most important first"""

VARIOUS_ARTISTS_VALUES = 'V.A.', 'various artists', 'Various Artists'
"""Values for ~people representing lots of people, most important last"""


def decode_value(tag, value):
    """Returns a unicode representation of the passed value, based on
    the type and the tag it originated from.

    Not reversible.
    """

    if isinstance(value, text_type):
        return value
    elif isinstance(value, float):
        return u"%.2f" % value
    elif tag in FILESYSTEM_TAGS:
        return fsdecode(value)
    return unicode(value)


class AudioFile(dict, ImageContainer):
    """An audio file. It looks like a dict, but implements synthetic
    and tied tags via __call__ rather than __getitem__. This means
    __getitem__, get, and so on can be used for efficiency.

    If you need to sort many AudioFiles, you can use their sort_key
    attribute as a decoration.

    Keys are either ASCII str or unicode.
    Values are always unicode except if the tag is part of FILESYSTEM_TAGS,
    then the value is of the path type (str on UNIX, unicode on Windows)

    Some methods will make sure the returned values are always unicode, see
    their description.
    """

    # New tags received from the backend will update the song
    fill_metadata = False
    # New song duration from the backend will update the song
    fill_length = False
    # Container for multiple songs, while played new songs can start/end
    multisong = False
    # Part of a multisong
    streamsong = False
    # Can be added to the queue, playlists
    can_add = True
    # Is a real file
    is_file = True

    format = "Unknown Audio File"
    mimes = []

    def __song_key(self):
        return (self("~#disc"), self("~#track"),
            human(self("artistsort")),
            self.get("musicbrainz_artistid", ""),
            human(self.get("title", "")),
            self.get("~filename"))

    @util.cached_property
    def album_key(self):
        return (human(self("albumsort", "")),
                human(self("albumartistsort", "")),
                self.get("album_grouping_key") or self.get("labelid") or
                self.get("musicbrainz_albumid") or "")

    @util.cached_property
    def sort_key(self):
        return [self.album_key, self.__song_key()]

    @staticmethod
    def sort_by_func(tag):
        """Returns a fast sort function for a specific tag (or pattern).
        Some keys are already in the sort cache, so we can use them."""
        def artist_sort(song):
            return song.sort_key[1][2]

        if callable(tag):
            return lambda song: human(tag(song))
        elif tag == "artistsort":
            return artist_sort
        elif tag in FILESYSTEM_TAGS:
            return lambda song: fsdecode(song(tag), note=False)
        elif tag.startswith("~#") and "~" not in tag[2:]:
            return lambda song: song(tag)
        return lambda song: human(song(tag))

    def __getstate__(self):
        """Don't pickle anything from __dict__"""
        pass

    def __setstate__(self, state):
        """Needed because we have defined getstate"""
        pass

    def __setitem__(self, key, value):
        if not self.__dict__:
            # unpickle case.. we can't fail
            dict.__setitem__(self, key, value)
            return

        if key.startswith("~#"):
            assert isinstance(value, number_types)
        elif key in FILESYSTEM_TAGS:
            assert is_fsnative(value)
        else:
            value = text_type(value)

        dict.__setitem__(self, key, value)

        pop = self.__dict__.pop
        pop("album_key", None)
        pop("sort_key", None)

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        if not self.__dict__:
            return
        pop = self.__dict__.pop
        pop("album_key", None)
        pop("sort_key", None)

    @property
    def key(self):
        return self["~filename"]

    @property
    def mountpoint(self):
        return self["~mountpoint"]

    def __hash__(self):
        # Dicts aren't hashable by default, so we need a hash
        # function. Previously this used ~filename. That created a
        # situation when an object could end up in two buckets by
        # renaming files. So now it uses identity.
        return hash(id(self))

    def __eq__(self, other):
        # And to preserve Python hash rules, we need a strict __eq__.
        return self is other

    def __lt__(self, other):
        return self.sort_key < other.sort_key

    def __ne__(self, other):
        return self is not other

    def reload(self):
        """Reload an audio file from disk. The caller is responsible for
        handling any errors."""

        fn = self["~filename"]
        saved = {}
        for key in self:
            if key in MIGRATE:
                saved[key] = self[key]
        self.clear()
        self["~filename"] = fn
        self.__init__(fn)
        self.update(saved)

    def realkeys(self):
        """Returns a list of keys that are not internal, i.e. they don't
        have '~' in them."""

        return filter(lambda s: s[:1] != "~", self.keys())

    def prefixkeys(self, prefix):
        """Returns a list of dict keys that either match prefix or start
        with prefix + ':'.
        """

        l = []
        for k in self:
            if k.startswith(prefix):
                if k == prefix or k.startswith(prefix + ":"):
                    l.append(k)
        return l

    def _prefixvalue(self, tag):
        return "\n".join(self.list_unique(sorted(self.prefixkeys(tag))))

    def iterrealitems(self):
        return ((k, v) for (k, v) in iteritems(self) if k[:1] != "~")

    def __call__(self, key, default=u"", connector=" - "):
        """Return a key, synthesizing it if necessary. A default value
        may be given (like dict.get); the default default is an empty
        unicode string (even if the tag is numeric).

        If a tied tag ('a~b') is requested, the 'connector' keyword
        argument may be used to specify what it is tied with.
        In case the tied tag contains numeric and file path tags, the result
        will still be a unicode string.

        For details on tied tags, see the documentation for util.tagsplit.
        """

        if key[:1] == "~":
            key = key[1:]
            if "~" in key:
                real_key = "~" + key
                values = []
                for v in map(self.__call__, util.tagsplit(real_key)):
                    v = decode_value(real_key, v)
                    if v:
                        values.append(v)
                return connector.join(values) or default
            elif key == "#track":
                try:
                    return int(self["tracknumber"].split("/")[0])
                except (ValueError, TypeError, KeyError):
                    return default
            elif key == "#disc":
                try:
                    return int(self["discnumber"].split("/")[0])
                except (ValueError, TypeError, KeyError):
                    return default
            elif key == "length":
                length = self.get("~#length")
                if length is None:
                    return default
                else:
                    return util.format_time_display(length)
            elif key == "#rating":
                return dict.get(self, "~" + key, config.RATINGS.default)
            elif key == "rating":
                return util.format_rating(self("~#rating"))
            elif key == "people":
                return "\n".join(self.list_unique(PEOPLE)) or default
            elif key == "people:real":
                # Issue 1034: Allow removal of V.A. if others exist.
                unique = self.list_unique(PEOPLE)
                # Order is important, for (unlikely case): multiple removals
                for val in VARIOUS_ARTISTS_VALUES:
                    if len(unique) > 1 and val in unique:
                        unique.remove(val)
                return "\n".join(unique) or default
            elif key == "people:roles":
                return (self._role_call("performer", PEOPLE)
                        or default)
            elif key == "peoplesort":
                return ("\n".join(self.list_unique(PEOPLE_SORT)) or
                        self("~people", default, connector))
            elif key == "peoplesort:roles":
                # Ignores non-sort tags if there are any sort tags (e.g. just
                # returns "B" for {artist=A, performersort=B}).
                # TODO: figure out the "correct" behavior for mixed sort tags
                return (self._role_call("performersort", PEOPLE_SORT)
                        or self("~peoplesort", default, connector))
            elif key in ("performers", "performer"):
                return self._prefixvalue("performer") or default
            elif key in ("performerssort", "performersort"):
                return (self._prefixvalue("performersort") or
                        self("~" + key[-4:], default, connector))
            elif key in ("performers:roles", "performer:roles"):
                return (self._role_call("performer") or default)
            elif key in ("performerssort:roles", "performersort:roles"):
                return (self._role_call("performersort")
                        or self("~" + key.replace("sort", ""), default,
                                connector))
            elif key == "basename":
                return os.path.basename(self["~filename"]) or self["~filename"]
            elif key == "dirname":
                return os.path.dirname(self["~filename"]) or self["~filename"]
            elif key == "uri":
                try:
                    return self["~uri"]
                except KeyError:
                    return URI.frompath(self["~filename"])
            elif key == "format":
                return self.get("~format", self.format)
            elif key == "codec":
                codec = self.get("~codec")
                if codec is None:
                    return self("~format")
                return codec
            elif key == "encoding":
                parts = filter(None,
                               [self.get("~encoding"), self.get("encodedby")])
                encoding = u"\n".join(parts)
                return encoding or default
            elif key == "language":
                codes = self.list("language")
                if not codes:
                    return default
                return u"\n".join(iso639.translate(c) or c for c in codes)
            elif key == "bitrate":
                return util.format_bitrate(self("~#bitrate"))
            elif key == "#date":
                date = self.get("date")
                if date is None:
                    return default
                return util.date_key(date)
            elif key == "year":
                return self.get("date", default)[:4]
            elif key == "#year":
                try:
                    return int(self.get("date", default)[:4])
                except (ValueError, TypeError, KeyError):
                    return default
            elif key == "originalyear":
                return self.get("originaldate", default)[:4]
            elif key == "#originalyear":
                try:
                    return int(self.get("originaldate", default)[:4])
                except (ValueError, TypeError, KeyError):
                    return default
            elif key == "#tracks":
                try:
                    return int(self["tracknumber"].split("/")[1])
                except (ValueError, IndexError, TypeError, KeyError):
                    return default
            elif key == "#discs":
                try:
                    return int(self["discnumber"].split("/")[1])
                except (ValueError, IndexError, TypeError, KeyError):
                    return default
            elif key == "lyrics":
                # First, try the embedded lyrics.
                try:
                    return self[key]
                except KeyError:
                    pass

                # If there are no embedded lyrics, try to read them from
                # the external file.
                try:
                    fileobj = open(self.lyric_filename, "rU")
                except EnvironmentError:
                    return default
                else:
                    return fileobj.read().decode("utf-8", "replace")
            elif key == "filesize":
                return util.format_size(self("~#filesize", 0))
            elif key == "playlists":
                # See Issue 876
                # Avoid circular references from formats/__init__.py
                from quodlibet.util.collection import Playlist
                playlists = Playlist.playlists_featuring(self)
                return "\n".join([s.name for s in playlists]) or default
            elif key.startswith("#replaygain_"):
                try:
                    val = self.get(key[1:], default)
                    return round(float(val.split(" ")[0]), 2)
                except (ValueError, TypeError, AttributeError):
                    return default
            elif key[:1] == "#":
                key = "~" + key
                if key in self:
                    return self[key]
                elif key in INTERN_NUM_DEFAULT:
                    return dict.get(self, key, 0)
                else:
                    try:
                        val = self[key[2:]]
                    except KeyError:
                        return default
                    try:
                        return int(val)
                    except ValueError:
                        try:
                            return float(val)
                        except ValueError:
                            return default
            else:
                return dict.get(self, "~" + key, default)

        elif key == "title":
            title = dict.get(self, "title")
            if title is None:
                basename = self("~basename")
                return "%s [%s]" % (
                    decode_value("~basename", basename), _("Unknown"))
            else:
                return title
        elif key in SORT_TO_TAG:
            try:
                return self[key]
            except KeyError:
                key = SORT_TO_TAG[key]
        return dict.get(self, key, default)

    def _role_call(self, role_tag, sub_keys=None):
        role_tag_keys = self.prefixkeys(role_tag)

        role_map = {}
        for key in role_tag_keys:
            if key != role_tag:
                role = key.rsplit(":", 1)[-1]
                for name in self.list(key):
                    role_map.setdefault(name, []).append(role)

        if sub_keys is None:
            names = self.list_unique(role_tag_keys)
        else:
            names = self.list_unique(sub_keys)
            for tag in sub_keys:
                if tag in TAG_ROLES:
                    for name in self.list(tag):
                        role_map.setdefault(name, []).append(TAG_ROLES[tag])

        descs = []
        for name in names:
            roles = role_map.get(name, [])
            if not roles:
                descs.append(name)
            else:
                roles = sorted(map(capitalize, roles))
                descs.append("%s (%s)" % (name, ", ".join(roles)))

        return "\n".join(descs)

    @property
    def lyric_filename(self):
        """Returns the (potential) lyrics filename for this file"""

        filename = self.comma("title").replace(u'/', u'')[:128] + u'.lyric'
        sub_dir = ((self.comma("lyricist") or self.comma("artist"))
                  .replace(u'/', u'')[:128])

        if os.name == "nt":
            # this was added at a later point. only use escape_filename here
            # to keep the linux case the same as before
            filename = escape_filename(filename)
            sub_dir = escape_filename(sub_dir)
        else:
            filename = fsnative(filename)
            sub_dir = fsnative(sub_dir)

        path = os.path.join(
            expanduser(fsnative(u"~/.lyrics")), sub_dir, filename)
        return path

    @property
    def has_rating(self):
        """True if the song has a rating set.

        In case this is False song('~#rating') would return the default value
        """

        return self.get("~#rating") is not None

    def remove_rating(self):
        """Removes the set rating so the default will be returned"""

        self.pop("~#rating", None)

    def comma(self, key):
        """Get all values of a tag, separated by commas. Synthetic
        tags are supported, but will be slower. All list items
        will be unicode.

        If the value is numeric, that is returned rather than a list.
        """

        if "~" in key or key == "title":
            v = self(key, u"")
            if key in FILESYSTEM_TAGS:
                v = fsdecode(v)
        else:
            v = self.get(key, u"")

        if isinstance(v, (int, long, float)):
            return v
        else:
            return v.replace("\n", ", ")

    def list(self, key):
        """Get all values of a tag, as a list. Synthetic tags are supported,
        but will be slower. Numeric tags are not supported.

        For file path keys the returned list might contain path items
        (non-unicode).

        An empty synthetic tag cannot be distinguished from a non-existent
        synthetic tag; both result in [].
        """

        if "~" in key or key == "title":
            v = self(key, connector="\n")
            if v == "":
                return []
            else:
                return v.split("\n")
        else:
            v = self.get(key)
            return [] if v is None else v.split("\n")

    def list_sort(self, key):
        """Like list but return display,sort pairs when appropriate
        and work on all tags
        """
        display = decode_value(key, self(key))
        display = display.split("\n") if display else []
        sort = []
        if key in TAG_TO_SORT:
            sort = decode_value(TAG_TO_SORT[key],
                                self(TAG_TO_SORT[key]))
            # it would be better to use something that doesn't fall back
            # to the key itself, but what?
            sort = sort.split("\n") if sort else []
        result = []
        for d, s in izip_longest(display, sort):
            if d is not None:
                result.append((d, s if s is not None and s != "" else d))
        return result

    def list_separate(self, key):
        """For tied tags return the list union of the display,sort values
           otherwise just do list_sort
        """
        if key[:1] == "~" and "~" in key[1:]: # tied tag
            vals = [self.list_sort(tag) for tag in util.tagsplit(key)]
            r = [j for i in vals for j in i]
            return r
        else:
            return self.list_sort(key)

    def list_unique(self, keys):
        """Returns a combined value of all values in keys; duplicate values
        will be ignored.

        Returns the same as list().
        """

        l = []
        seen = set()
        for k in keys:
            for v in self.list(k):
                if v not in seen:
                    l.append(v)
                    seen.add(v)
        return l

    def as_lowercased(self):
        """Returns a new AudioFile with all keys lowercased / values merged.

        Useful for tag writing for case insensitive tagging formats like
        APEv2 or VorbisComment.
        """

        merged = AudioFile()
        text = {}
        for key, value in iteritems(self):
            lower = key.lower()
            if key.startswith("~#"):
                merged[lower] = value
            else:
                text.setdefault(lower, []).extend(value.split("\n"))
        for key, values in text.items():
            merged[key] = "\n".join(values)
        return merged

    def exists(self):
        """Return true if the file still exists (or we can't tell)."""

        return os.path.exists(self["~filename"])

    def valid(self):
        """Return true if the file cache is up-to-date (checked via
        mtime), or we can't tell."""
        return (bool(self.get("~#mtime", 0)) and
                self["~#mtime"] == mtime(self["~filename"]))

    def mounted(self):
        """Return true if the disk the file is on is mounted, or
        the file is not on a disk."""
        return os.path.ismount(self.get("~mountpoint", "/"))

    def can_multiple_values(self, key=None):
        """If no arguments are given, return a list of tags that can
        have multiple values, or True if 'any' tags can.
        """

        return True

    def can_change(self, k=None):
        """See if this file supports changing the given tag. This may
        be a limitation of the file type or QL's design.

        The writing code should handle all kinds of keys, so this is
        just a suggestion.

        If no arguments are given, return a list of tags that can be
        changed, or True if 'any' tags can be changed (specific tags
        should be checked before adding)."""

        if k is None:
            return True

        if not isascii(k):
            return False

        if not k or "=" in k or "~" in k:
            return False

        return True

    def is_writable(self):
        return os.access(self["~filename"], os.W_OK)

    def rename(self, newname):
        """Rename a file. Errors are not handled. This shouldn't be used
        directly; use library.rename instead."""

        if os.path.isabs(newname):
            mkdir(os.path.dirname(newname))
        else:
            newname = os.path.join(self('~dirname'), newname)

        if not os.path.exists(newname):
            shutil.move(self['~filename'], newname)
        elif normalize_path(newname, canonicalise=True) != self['~filename']:
            raise ValueError

        self.sanitize(newname)

    def website(self):
        """Look for a URL in the audio metadata, or a Google search
        if no URL can be found."""

        if "website" in self:
            return self.list("website")[0]
        for cont in self.list("contact") + self.list("comment"):
            c = cont.lower()
            if (c.startswith("http://") or c.startswith("https://") or
                    c.startswith("www.")):
                return cont
            elif c.startswith("//www."):
                return "http:" + cont
        else:
            text = "http://www.google.com/search?q="
            esc = lambda c: ord(c) > 127 and '%%%x' % ord(c) or c
            if "labelid" in self:
                text += ''.join(map(esc, self["labelid"]))
            else:
                artist = util.escape("+".join(self("artist").split()))
                album = util.escape("+".join(self("album").split()))
                artist = encode(artist)
                album = encode(album)
                artist = "%22" + ''.join(map(esc, artist)) + "%22"
                album = "%22" + ''.join(map(esc, album)) + "%22"
                text += artist + "+" + album
            text += "&ie=UTF8"
            return text

    def sanitize(self, filename=None):
        """Fill in metadata defaults. Find ~mountpoint, ~#mtime, ~#filesize
        and ~#added. Check for null bytes in tags."""

        # Replace nulls with newlines, trimming zero-length segments
        for key, val in self.items():
            if isinstance(val, string_types) and '\0' in val:
                self[key] = '\n'.join(filter(lambda s: s, val.split('\0')))
            # Remove unnecessary defaults
            if key in INTERN_NUM_DEFAULT and val == 0:
                del self[key]

        if filename:
            self["~filename"] = filename
        elif "~filename" not in self:
            raise ValueError("Unknown filename!")

        assert is_fsnative(self["~filename"])

        if self.is_file:
            self["~filename"] = normalize_path(
                self["~filename"], canonicalise=True)
            # Find mount point (terminating at "/" if necessary)
            head = self["~filename"]
            while "~mountpoint" not in self:
                head, tail = os.path.split(head)
                # Prevent infinite loop without a fully-qualified filename
                # (the unit tests use these).
                head = head or "/"
                if os.path.ismount(head):
                    self["~mountpoint"] = head
        else:
            self["~mountpoint"] = fsnative(u"/")

        # Fill in necessary values.
        self.setdefault("~#added", int(time.time()))

        # For efficiency, do a single stat here. See Issue 504
        try:
            stat = os.stat(self['~filename'])
            self["~#mtime"] = stat.st_mtime
            self["~#filesize"] = stat.st_size

            # Issue 342. This is a horrible approximation (due to headers) but
            # on FLACs, the most common case, this should be close enough
            if "~#bitrate" not in self:
                try:
                    # kbps = bytes * 8 / seconds / 1000
                    self["~#bitrate"] = int(stat.st_size /
                                            (self["~#length"] * (1000 / 8)))
                except (KeyError, ZeroDivisionError):
                    pass
        except OSError:
            self["~#mtime"] = 0

    def to_dump(self):
        """A string of 'key=value' lines, similar to vorbiscomment output."""

        def encode_key(k):
            return encode(k) if isinstance(k, text_type) else k

        s = []
        for k in self.keys():
            enc_key = encode_key(k)

            if isinstance(self[k], int) or isinstance(self[k], long):
                s.append("%s=%d" % (enc_key, self[k]))
            elif isinstance(self[k], float):
                s.append("%s=%f" % (enc_key, self[k]))
            else:
                for v2 in self.list(k):
                    if isinstance(v2, str):
                        s.append("%s=%s" % (enc_key, v2))
                    else:
                        s.append("%s=%s" % (enc_key, encode(v2)))
        for k in (INTERN_NUM_DEFAULT - set(self.keys())):
            enc_key = encode_key(k)
            s.append("%s=%d" % (enc_key, self.get(k, 0)))
        if "~#rating" not in self:
            s.append("~#rating=%f" % self("~#rating"))
        s.append("~format=%s" % self.format)
        s.append("")
        return "\n".join(s)

    def from_dump(self, text):
        """Parses the text created with to_dump and adds the found tags."""

        def decode_key(key):
            """str if ascii, otherwise decode using utf-8"""
            try:
                key.decode("ascii")
            except ValueError:
                return decode(key)
            return key

        for line in text.split("\n"):
            if not line:
                continue
            parts = line.split("=")
            key = parts[0]
            val = "=".join(parts[1:])
            if key == "~format":
                pass
            elif key.startswith("~#"):
                try:
                    self.add(key, int(val))
                except ValueError:
                    try:
                        self.add(key, float(val))
                    except ValueError:
                        pass
            else:
                self.add(decode_key(key), decode(val))

    def change(self, key, old_value, new_value):
        """Change 'old_value' to 'new_value' for the given metadata key.
        If the old value is not found, set the key to the new value."""
        try:
            parts = self.list(key)
            try:
                parts[parts.index(old_value)] = new_value
            except ValueError:
                self[key] = new_value
            else:
                self[key] = "\n".join(parts)
        except KeyError:
            self[key] = new_value

    def add(self, key, value):
        """Add a value for the given metadata key."""
        if key not in self:
            self[key] = value
        else:
            self[key] += "\n" + value

    def remove(self, key, value=None):
        """Remove a value from the given key.

        If value is None remove all values for that key, if it exists.
        If the key or value is not found do nothing.
        """

        if key not in self:
            return
        elif value is None or self[key] == value:
            del self[key]
        else:
            try:
                parts = self.list(key)
                parts.remove(value)
                self[key] = u"\n".join(parts)
            except ValueError:
                pass

    def replay_gain(self, profiles, pre_amp_gain=0, fallback_gain=0):
        """Return the computed Replay Gain scale factor.

        profiles is a list of Replay Gain profile names ('album',
        'track') to try before giving up. The special profile name
        'none' will cause no scaling to occur. pre_amp_gain will be
        applied before checking for clipping. fallback_gain will be
        used when the song does not have replaygain information.
        """
        for profile in profiles:
            if profile is "none":
                return 1.0
            try:
                db = float(self["replaygain_%s_gain" % profile].split()[0])
                peak = float(self.get("replaygain_%s_peak" % profile, 1))
            except (KeyError, ValueError, IndexError):
                continue
            else:
                db += pre_amp_gain
                scale = 10. ** (db / 20)
                if scale * peak > 1:
                    scale = 1.0 / peak  # don't clip
                return min(15, scale)
        else:
            scale = 10. ** ((fallback_gain + pre_amp_gain) / 20)
            if scale > 1:
                scale = 1.0  # don't clip
            return min(15, scale)

    def write(self):
        """Write metadata back to the file."""
        raise NotImplementedError

    @property
    def bookmarks(self):
        """Parse and return song position bookmarks, or set them.
        Accessing this returns a copy, so song.bookmarks.append(...)
        will not work; you need to do

            marks = song.bookmarks
            marks.append(...)
            song.bookmarks = marks
        """

        marks = []
        invalid = []
        for line in self.list("~bookmark"):
            try:
                time, mark = line.split(" ", 1)
            except:
                invalid.append((-1, line))
            else:
                try:
                    time = util.parse_time(time, None)
                except:
                    invalid.append((-1, line))
                else:
                    if time >= 0:
                        marks.append((time, mark))
                    else:
                        invalid.append((-1, line))
        marks.sort()
        marks.extend(invalid)
        return marks

    @bookmarks.setter
    def bookmarks(self, marks):
        result = []
        for time_, mark in marks:
            if time_ < 0:
                raise ValueError("mark times must be positive")
            result.append(u"%s %s" % (util.format_time(time_), mark))
        result = u"\n".join(result)
        if result:
            self["~bookmark"] = result
        elif "~bookmark" in self:
            del(self["~bookmark"])


# Looks like the real thing.
DUMMY_SONG = AudioFile({
    '~#length': 234, '~filename': '/dev/null',
    'artist': 'The Artist', 'album': 'An Example Album',
    'title': 'First Track', 'tracknumber': 1,
    'date': '2010-12-31',
})
