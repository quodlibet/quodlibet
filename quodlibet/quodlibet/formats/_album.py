# -*- coding: utf-8 -*-
# Copyright 2004-2010 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gobject

from quodlibet import util
from quodlibet import config
from quodlibet.formats._audio import PEOPLE, TAG_TO_SORT, INTERN_NUM_DEFAULT
from quodlibet.util import thumbnails

ELPOEP = list(reversed(PEOPLE))
PEOPLE_SCORE = [100**i for i in xrange(len(PEOPLE))]

NUM_DEFAULT_FUNCS = {
    "length": "sum",
    "playcount": "sum",
    "added": "max",
    "lastplayed": "max",
    "laststarted": "max",
    "mtime": "max",
    "rating": "avg",
    "skipcount": "sum",
    "year": "min",
    "filesize": "sum"
}

NUM_FUNCS = {
    "max": max, "min": min, "sum": sum,
    "avg": lambda s: float(sum(s)) / len(s)
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
        """Call this after songs got added or removed"""
        self.__cache.clear()
        self.__default.clear()
        self.__used = []

    def get(self, key, default=u"", connector=u" - "):
        if not self.songs:
            return default
        if key[:1] == "~" and "~" in key[1:]:
            if not isinstance(default, basestring): return default
            keys = util.tagsplit(key)
            v = map(self.__get_cached_value, keys)
            def default_funct(x):
                if x is None: return default
                return x
            v = map(default_funct , v)
            v = map(lambda x: (isinstance(x, float) and "%.2f" % x) or x, v)
            v = map(lambda x: isinstance(x, basestring) and x or str(x), v)
            return  connector.join(filter(None, v)) or default
        else:
            value = self.__get_cached_value(key)
            if value is None:
                return default
            return value

    __call__ = get

    def comma(self, key):
        value = self.get(key)
        if isinstance(value, (int, float)): return value
        return value.replace("\n", ", ")

    def list(self, key):
        if "~" in key[1:]:
            v = self.get(key, connector=u"\n")
        else: v = self.get(key)
        if v == "": return []
        else: return v.split("\n")
        return []

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
            # remove the oldest if the cache is full
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
                if not length: return 0
                w = lambda s: s("~#bitrate", 0) * s("~#length", 0)
                return sum(w(song) for song in self.songs) / length
            elif key in NUM_DEFAULT_FUNCS:
                func = NUM_DEFAULT_FUNCS[key]
            else:
                #Unknown key. AudioFile will try to cast the values to int,
                #default to avg
                func = "avg"

            key = "~#" + key

            func = NUM_FUNCS.get(func)
            if func:
                #if none of the songs can return a numeric key
                #the album returns default
                values = (song(key) for song in self.songs)
                values = [v for v in values if v != ""]
                if values: return func(values)
                else: return None
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
                #It's cheaper to get people and peoplesort in one go
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
                if length is None: return None
                return util.format_time(length)
            elif key == "long-length":
                length = self.__get_value("~#length")
                if length is None: return None
                return util.format_time_long(length)
            elif key == "tracks":
                tracks = self.__get_value("~#tracks")
                if tracks is None: return None
                return ngettext("%d track", "%d tracks", tracks) % tracks
            elif key == "discs":
                discs = self.__get_value("~#discs")
                if discs > 1:
                    return ngettext("%d disc", "%d discs", discs) % discs
                else: return None
            elif key == "rating":
                rating = self.__get_value("~#rating")
                if rating is None: return None
                return util.format_rating(rating)
            elif key == "cover":
                return ((self.cover != type(self).cover) and "y") or None
            elif key == "filesize":
                size = self.__get_value("~#filesize")
                if size is None: return None
                return util.format_size(size)
            key = "~" + key

        #Nothing special was found, so just take all values of the songs
        #and sort them by their number of appearance
        result = {}
        for song in self.songs:
            for value in song.list(key):
                result[value] = result.get(value, 0) - 1

        values = map(lambda x: x[0],
            sorted(result.items(), key=lambda x: x[1]))
        if not values: return None
        return "\n".join(values)

class Album(Collection):
    """Like a collection but adds cover scanning, some atributes for sorting
    and uses a set for the songs."""

    cover = None
    scanned = False

    @util.cached_property
    def peoplesort(self):
        val = self.get("~peoplesort").split("\n")
        return map(util.human_sort_key, val)

    date = property(lambda self: self.get("date"))
    title = property(lambda self: self.get("album"))

    def __init__(self, song):
        super(Album, self).__init__()
        self.songs = set()
        #albumsort is part of the album_key, so every song has the same
        self.sort = util.human_sort_key(song("albumsort"))
        self.key = song.album_key

    def finalize(self):
        """Call this after songs got added or removed"""
        super(Album, self).finalize()
        self.__dict__.pop("peoplesort", None)

    def scan_cover(self):
        if self.scanned or not self.songs: return
        self.scanned = True

        song = iter(self.songs).next()
        cover = song.find_cover()

        if cover is not None:
            try:
                round = config.getboolean("settings", "round")
                self.cover = thumbnails.get_thumbnail(cover.name, (48, 48))
                self.cover = thumbnails.add_border(self.cover, 30, round)
            except gobject.GError:
                return

    def __repr__(self):
        return "Album(%s)" % repr(self.key)
