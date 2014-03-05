# -*- coding: utf-8 -*-
# Copyright 2004-2013 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from __future__ import absolute_import

from gi.repository import GLib

import os
import random

from quodlibet import util
from quodlibet import config
from quodlibet.formats._audio import PEOPLE, TAG_TO_SORT, INTERN_NUM_DEFAULT
from quodlibet.util import thumbnails
from collections import Iterable
from quodlibet.util.path import fsencode, escape_filename, unescape_filename
from .collections import HashedList


ELPOEP = list(reversed(PEOPLE))
PEOPLE_SCORE = [100 ** i for i in xrange(len(PEOPLE))]


def avg(nums):
    """Returns the average (arithmetic mean) of a list of numbers"""
    return float(sum(nums)) / len(nums)


def bayesian_average(nums, c=None, m=None):
    """Returns the Bayesian average of an iterable of numbers,
    with parameters defaulting to config specific to ~#rating."""
    m = m or config.RATINGS.default
    c = c or config.getfloat("settings", "bayesian_rating_factor", 0.0)
    ret = float(m * c + sum(nums)) / (c + len(nums))
    return ret

NUM_DEFAULT_FUNCS = {
    "length": "sum",
    "playcount": "sum",
    "added": "max",
    "lastplayed": "max",
    "laststarted": "max",
    "mtime": "max",
    "rating": "bav",
    "skipcount": "sum",
    "year": "min",
    "originalyear": "min",
    "filesize": "sum"
}

NUM_FUNCS = {
    "max": max,
    "min": min,
    "sum": sum,
    "avg": avg,
    "bav": bayesian_average
}


class Collection(object):
    """A collection of songs which implements some methods similar to the
    AudioFile class.

    The content of the collection can be changed by changing the content of
    the songs attribute.
    """

    _cache_size = 6
    songs = ()

    def __init__(self):
        """Cache in _cache, LRU key order in _used, keys that return default
        are in _default"""
        self.__cache = {}
        self.__default = set()
        self.__used = []

    def finalize(self):
        """Finalize the collection.
        Call this after songs get added or removed"""
        self.__cache.clear()
        self.__default.clear()
        self.__used = []

    def get(self, key, default=u"", connector=u" - "):
        if not self.songs:
            return default
        if key[:1] == "~" and "~" in key[1:]:
            if not isinstance(default, basestring):
                return default
            keys = util.tagsplit(key)
            v = map(self.__get_cached_value, keys)

            def default_funct(x):
                if x is None:
                    return default
                return x
            v = map(default_funct, v)
            v = map(lambda x: (isinstance(x, float) and "%.2f" % x) or x, v)
            v = map(lambda x: isinstance(x, basestring) and x or str(x), v)
            return connector.join(filter(None, v)) or default
        else:
            value = self.__get_cached_value(key)
            if value is None:
                return default
            return value

    __call__ = get

    def comma(self, key):
        value = self.get(key)
        return (value if isinstance(value, (int, float, long))
                else value.replace("\n", ", "))

    def list(self, key):
        v = self.get(key, connector=u"\n") if "~" in key[1:] else self.get(key)
        return [] if v == "" else v.split("\n")

    def __get_cached_value(self, key):
        if key in self.__cache:
            self.__used.remove(key)
            self.__used.insert(0, key)
            return self.__cache[key]
        elif key in self.__default:
            return None
        else:
            val = self.__get_value(key)
            if val is None:
                self.__default.add(key)
            else:
                self.__used.insert(0, key)
                self.__cache[key] = val
            # Remove the oldest if the cache is full
            if len(self.__used) > self._cache_size:
                self.__cache.pop(self.__used.pop(-1))
        return val

    def __get_value(self, key):
        """This is similar to __call__ in the AudioFile class.
        All internal tags are changed to represent a collection of songs.
        """

        # Using key:<func> runs the resulting list of values
        # through the function before returning it.
        # Numeric keys without a func will default to a reasonable function
        if key.startswith("~#"):
            key = key[2:]

            if key[-4:-3] == ":":
                func = key[-3:]
                key = key[:-4]
            elif key == "tracks":
                return len(self.songs)
            elif key == "discs":
                return len(set([song("~#disc", 1) for song in self.songs]))
            elif key == "bitrate":
                length = self.__get_value("~#length")
                if not length:
                    return 0
                w = lambda s: s("~#bitrate", 0) * s("~#length", 0)
                return sum(w(song) for song in self.songs) / length
            else:
                # Unknown key. AudioFile will try to cast the values to int,
                # default to avg
                func = NUM_DEFAULT_FUNCS.get(key, "avg")

            key = "~#" + key
            func = NUM_FUNCS.get(func)
            if func:
                # If none of the songs can return a numeric key,
                # the album returns default
                values = (song(key) for song in self.songs)
                values = [v for v in values if v != ""]
                return func(values) if values else None
            elif key in INTERN_NUM_DEFAULT:
                return 0
            return None
        elif key[:1] == "~":
            key = key[1:]
            keys = {"people": {}, "peoplesort": {}}
            if key in keys:
                people = keys["people"]
                peoplesort = keys["peoplesort"]
                for song in self.songs:
                    # Rank people by "relevance" -- artists before composers
                    # before performers, then by number of appearances.
                    for w, k in enumerate(ELPOEP):
                        persons = song.list(k)
                        for person in persons:
                            people[person] = (people.get(person, 0) -
                                              PEOPLE_SCORE[w])
                        if k in TAG_TO_SORT:
                            persons = song.list(TAG_TO_SORT[k]) or persons
                        for person in persons:
                            peoplesort[person] = (peoplesort.get(person, 0) -
                                                  PEOPLE_SCORE[w])
                # It's cheaper to get people and peoplesort in one go
                keys["people"] = sorted(people.keys(),
                                        key=people.__getitem__)[:100]
                keys["peoplesort"] = sorted(peoplesort.keys(),
                                            key=peoplesort.__getitem__)[:100]

                ret = keys.pop(key)
                ret = (ret and "\n".join(ret)) or None

                other, values = keys.popitem()
                other = "~" + other
                if not values:
                    self.__default.add(other)
                else:
                    if other in self.__used:
                        self.__used.remove(other)
                    self.__used.append(other)
                    self.__cache[other] = "\n".join(values)
                return ret
            elif key == "length":
                length = self.__get_value("~#length")
                return None if length is None else util.format_time(length)
            elif key == "long-length":
                length = self.__get_value("~#length")
                if length is None:
                    return None
                else:
                    return util.format_time_long(length)
            elif key == "tracks":
                tracks = self.__get_value("~#tracks")
                return (None if tracks is None else
                        ngettext("%d track", "%d tracks", tracks) % tracks)
            elif key == "discs":
                discs = self.__get_value("~#discs")
                if discs > 1:
                    return ngettext("%d disc", "%d discs", discs) % discs
                else:
                    # TODO: check this is correct for discs == 1
                    return None
            elif key == "rating":
                rating = self.__get_value("~#rating")
                if rating is None:
                    return None
                return util.format_rating(rating)
            elif key == "cover":
                return ((self.cover != type(self).cover) and "y") or None
            elif key == "filesize":
                size = self.__get_value("~#filesize")
                return None if size is None else util.format_size(size)
            key = "~" + key

        # Nothing special was found, so just take all values of the songs
        # and sort them by their number of appearance
        result = {}
        for song in self.songs:
            for value in song.list(key):
                result[value] = result.get(value, 0) - 1

        values = map(lambda x: x[0],
                     sorted(result.items(), key=lambda x: x[1]))
        return "\n".join(values) if values else None


class Album(Collection):
    """Like a `Collection` but adds cover scanning, some attributes for sorting
    and uses a set for the songs."""

    COVER_SIZE = 48

    cover = None
    scanned = False

    @util.cached_property
    def peoplesort(self):
        return util.human_sort_key(self.get("~peoplesort").split("\n")[0])

    @util.cached_property
    def genre(self):
        return util.human_sort_key(self.get("genre").split("\n")[0])

    date = property(lambda self: self.get("date"))
    title = property(lambda self: self.get("album"))

    def __init__(self, song):
        super(Album, self).__init__()
        self.songs = set()
        # albumsort is part of the album_key, so every song has the same
        self.sort = util.human_sort_key(song("albumsort"))
        self.key = song.album_key

    @property
    def str_key(self):
        return str(self.key)

    def finalize(self):
        """Finalize this album. Call after songs get added or removed"""
        super(Album, self).finalize()
        self.__dict__.pop("peoplesort", None)
        self.__dict__.pop("genre", None)

    def scan_cover(self, force=False):
        if (self.scanned and not force) or not self.songs:
            return
        self.scanned = True

        song = iter(self.songs).next()
        cover = song.find_cover()

        if cover is not None:
            s = self.COVER_SIZE
            try:
                round = config.getboolean("albumart", "round")
                self.cover = thumbnails.get_thumbnail(cover.name, (s, s))
                self.cover = thumbnails.add_border(self.cover, 30, round)
            except GLib.GError:
                return

    def __repr__(self):
        return "Album(%s)" % repr(self.key)


class Playlist(Collection, Iterable):
    """A Playlist is a `Collection` that has list-like features
    Songs can appear more than once.

    TODO: Fix this crap
    """

    __instances = []

    quote = staticmethod(escape_filename)
    unquote = staticmethod(unescape_filename)

    @classmethod
    def new(cls, dir, base=_("New Playlist"), library={}):
        if not (dir and os.path.realpath(dir)):
            raise ValueError("Invalid playlist directory '%s'" % (dir,))
        p = Playlist(dir, "", library=library)
        i = 0
        try:
            p.rename(base)
        except ValueError:
            while not p.name:
                i += 1
                try:
                    p.rename("%s %d" % (base, i))
                except ValueError:
                    pass
        return p

    @classmethod
    def fromsongs(cls, dir, songs, library={}):
        if len(songs) == 1:
            title = songs[0].comma("title")
        else:
            title = ngettext(
                "%(title)s and %(count)d more",
                "%(title)s and %(count)d more",
                len(songs) - 1) % (
                    {'title': songs[0].comma("title"),
                     'count': len(songs) - 1})
        playlist = cls.new(dir, title, library=library)
        playlist.extend(songs)
        return playlist

    @classmethod
    def playlists_featuring(cls, song):
        """Returns the list of playlists in which this song appears"""
        playlists = []
        for instance in cls.__instances:
            if song in instance._list:
                playlists.append(instance)
        return playlists

    # List-like methods, for compatibilty with original Playlist class.
    def extend(self, songs):
        self._list.extend(songs)

    def append(self, song):
        return self._list.append(song)

    def clear(self):
        del self._list[:]

    def __iter__(self):
        return iter(self._list)

    def __len__(self):
        return len(self._list)

    def __getitem__(self, index):
        return self._list[index]

    def index(self, value):
        return self._list.index(value)

    def __setitem__(self, key, value):
        self._list[key] = value

    @property
    def songs(self):
        return [s for s in self._list if not isinstance(s, basestring)]

    def __init__(self, dir, name, library=None):
        super(Playlist, self).__init__()
        self.__instances.append(self)

        if isinstance(name, unicode) and os.name != "nt":
            name = name.encode('utf-8')

        self.name = name
        self.dir = dir
        self._list = HashedList()
        basename = self.quote(name)
        try:
            for line in file(os.path.join(self.dir, basename), "r"):
                line = util.fsnative(line.rstrip())
                if line in library:
                    self._list.append(library[line])
                elif library and library.masked(line):
                    self._list.append(line)
        except IOError:
            if self.name:
                self.write()

    def rename(self, newname):
        if isinstance(newname, unicode):
            newname = newname.encode('utf-8')

        if newname == self.name:
            return
        elif os.path.exists(os.path.join(self.dir, self.quote(newname))):
            raise ValueError(
                _("A playlist named %s already exists.") % newname)
        else:
            try:
                os.unlink(os.path.join(self.dir, self.quote(self.name)))
            except EnvironmentError:
                pass
            self.name = newname
            self.write()

    def add_songs(self, filenames, library):
        changed = False
        for i in range(len(self)):
            if isinstance(self[i], basestring) and self._list[i] in filenames:
                self._list[i] = library[self._list[i]]
                changed = True
        return changed

    def remove_songs(self, songs, library, leave_dupes=False):
        """Removes `songs` from this playlist if they are there,
         removing only the first reference if `leave_dupes` is True
        """
        changed = False
        for song in songs:
            # TODO: document the "library.masked" business
            if library.masked(song):
                while True:
                    try:
                        self._list[self.index(song)] = song("~filename")
                    except ValueError:
                        break
                    else:
                        changed = True
            else:
                while song in self._list:
                    self._list.remove(song)
                    if leave_dupes:
                        changed = True
                        break
                else:
                    changed = True
        return changed

    def has_songs(self, songs):
        # TODO(rm): consider the "library.masked" business
        some, all = False, True
        for song in songs:
            found = song in self._list
            some = some or found
            all = all and found
            if some and not all:
                break
        return some, all

    def delete(self):
        self.clear()
        try:
            os.unlink(os.path.join(self.dir, self.quote(self.name)))
        except EnvironmentError:
            pass
        if self in self.__instances:
            self.__instances.remove(self)

    def write(self):
        basename = self.quote(self.name)
        with open(os.path.join(self.dir, basename), "w") as f:
            for song in self._list:
                try:
                    f.write(fsencode(song("~filename")) + "\n")
                except TypeError:
                    f.write(song + "\n")

    def format(self):
        """Return a markup representation of information for this playlist"""
        total_size = float(self.get("~#filesize") or 0.0)
        songs_text = (ngettext("%d song", "%d songs", len(self.songs))
                      % len(self.songs))
        # see Issue 504
        return "<b>%s</b>\n<small>%s (%s%s)</small>" % (
               util.escape(self.name),
               songs_text,
               self.get("~length", "0:00"),
               " / %s" %
               util.format_size(total_size) if total_size > 0 else "")

    @property
    def has_duplicates(self):
        """Returns True if there are any duplicated files in this playlist"""
        return self._list.has_duplicates()

    def shuffle(self):
        """Randomly shuffles this playlist, without weighting"""
        random.shuffle(self._list)
        self.write()

    def __cmp__(self, other):
        try:
            return cmp(self.name, other.name)
        except AttributeError:
            return -1

    def __str__(self):
        songs_text = (ngettext("%d song", "%d songs", len(self.songs))
                      % len(self.songs))
        return "\"%s\" (%s)" % (self.name, songs_text)
