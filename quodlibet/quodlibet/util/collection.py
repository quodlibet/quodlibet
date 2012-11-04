# -*- coding: utf-8 -*-
# Copyright 2004-2012 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gobject
import os
import random

from quodlibet import util
from quodlibet import config
from quodlibet.formats._audio import PEOPLE, TAG_TO_SORT, INTERN_NUM_DEFAULT
from quodlibet.util import thumbnails
from quodlibet.util.dprint import print_d
from collections import Iterable

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
    "originalyear": "min",
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
    """Like a collection but adds cover scanning, some attributes for sorting
    and uses a set for the songs."""

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
        #albumsort is part of the album_key, so every song has the same
        self.sort = util.human_sort_key(song("albumsort"))
        self.key = song.album_key

    def finalize(self):
        """Call this after songs got added or removed"""
        super(Album, self).finalize()
        self.__dict__.pop("peoplesort", None)
        self.__dict__.pop("genre", None)

    def scan_cover(self, force=False):
        if (self.scanned and not force) or not self.songs: return
        self.scanned = True

        song = iter(self.songs).next()
        cover = song.find_cover()

        if cover is not None:
            try:
                round = config.getboolean("albumart", "round")
                self.cover = thumbnails.get_thumbnail(cover.name, (48, 48))
                self.cover = thumbnails.add_border(self.cover, 30, round)
            except gobject.GError:
                return

    def __repr__(self):
        return "Album(%s)" % repr(self.key)


class Playlist(Collection, Iterable):
    """A Playlist is a `Collection` that has list-like features
    Songs can appear more than once.
    """
    __instances = []
    _song_map_cache = {}
    _hits = 0
    _misses = 0

    @classmethod
    def _remove_all(cls):
        """De-registers all instances of Playlists"""
        cls.__instances = []

    quote = staticmethod(util.escape_filename)
    unquote = staticmethod(util.unescape_filename)

    @classmethod
    def new(cls, dir, base=_("New Playlist"), library={}):
        if not (dir and os.path.realpath(dir)):
            raise ValueError("Invalid playlist directory '%s'" % (dir,))
        p = Playlist(dir, "", library=library)
        i = 0
        try:p.rename(base)
        except ValueError:
            while not p.name:
                i += 1
                try: p.rename("%s %d" % (base, i))
                except ValueError: pass
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
                    {'title': songs[0].comma("title"), 'count': len(songs) - 1})
        playlist = cls.new(dir, title, library=library)
        playlist.extend(songs)
        return playlist

    @classmethod
    def _uncached_playlists_featuring(cls, song):
        """Returns the set of playlists this song appears in"""
        ret = set([])
        for pl in cls.__instances:
            if song in pl: ret.add(pl)
        return ret

    @classmethod
    def _cached_playlists_featuring(cls, song):
        """Returns the set of playlists this song appears in,
        using a global cache of unlimited size"""
        try:
            playlists = cls._song_map_cache[song]
            cls._hits += 1
        except KeyError:
            cls._misses += 1
            playlists = set([])
            if cls.__instances:
                for pl in cls.__instances:
                    if song in pl: playlists.add(pl)
                if not len(cls._song_map_cache) % 500:
                    print_d("Cache for %d playlists, of %d entries, is at %d KB"
                            %  (len(cls.__instances),
                                len(cls._song_map_cache),
                                cls._get_cache_size()))
                cls._song_map_cache[song] = playlists
        return playlists

    # Default to using the cached version
    playlists_featuring = _cached_playlists_featuring

    def __add_song_to_cache(self, song):
        print_d("Pre-caching \"%s\"..." % song("~filename"))
        try:
            playlists = self._song_map_cache[song]
            playlists.add(self)
        except KeyError:
            playlists = set([self])
            self._song_map_cache[song] = playlists

    def __remove_from_cache(self, song):
        """Removes this playlist from the global cache for `song`"""
        print_d("Evicting \"%s\" from cache for \"%s\"..." %
                (self.name, song['~filename']))
        try:
            self._song_map_cache[song].remove(self)
            # This may not be good. Depends how much songs come in and out
            if not self._song_map_cache[song]:
                del self._song_map_cache[song]
        except (KeyError, IndexError): return

    @classmethod
    def _clear_global_cache(cls):
        """Clears the entire song -> playlists cache"""
        cls._song_map_cache = {}

    @classmethod
    def _get_cache_size(cls):
        """Returns size in KB of current cache. For debugging mainly."""
        return cls._song_map_cache.__sizeof__() / 1024


    # List-like methods, for compatibilty with original Playlist class.
    def extend(self, songs):
        self.songs.extend(songs)
        for song in songs:
            self.__add_song_to_cache(song)

    def append(self, song):
        self.__add_song_to_cache(song)
        return self.songs.append(song)

    def clear(self):
        print_d("Removing all songs from \"%s\"" % self.name)
        for song in self.songs:
            self.__remove_from_cache(song)
        del self.songs[:]

    def __iter__(self):
        return iter(self.songs)

    def __len__(self):
        return len(self.songs)

    def __getitem__(self, item):
        # Support slices
        return self.songs.__getitem__(item)

    def index(self, value):
        return self.songs.index(value)

    def __setitem__(self, key, value):
        # TODO: more intelligent cache management
        for song in self.songs:
            self.__remove_from_cache(song)
        self.songs.__setitem__(key, value)
        for song in self.songs:
            self.__add_song_to_cache(song)

    def __init__(self, dir, name, library=None):
        super(Playlist, self).__init__()
        if isinstance(name, unicode) and os.name != "nt":
            name = name.encode('utf-8')
        self.name = name
        self.dir = dir
        self.songs = []
        self.__instances.append(self)
        basename = self.quote(name)
        try:
            for line in file(os.path.join(self.dir, basename), "r"):
                line = util.fsnative(line.rstrip())
                if line in library:
                    self.songs.append(library[line])
                elif library and library.masked(line):
                    self.songs.append(line)
        except IOError:
            if self.name: self.write()

    def rename(self, newname):
        if isinstance(newname, unicode): newname = newname.encode('utf-8')
        if newname == self.name: return
        elif os.path.exists(os.path.join(self.dir, self.quote(newname))):
            raise ValueError(
                _("A playlist named %s already exists.") % newname)
        else:
            try: os.unlink(os.path.join(self.dir, self.quote(self.name)))
            except EnvironmentError: pass
            self.name = newname
            self.write()

    def add_songs(self, filenames, library):
        changed = False
        for i in range(len(self)):
            if isinstance(self[i], basestring) and self.songs[i] in filenames:
                song = self.songs[i] = library[self.songs[i]]
                changed = True
                self.__add_song_to_cache(song)
        return changed

    def remove_songs(self, songs, library, leave_dupes=False):
        """
         Removes `songs` from this playlist if they are there,
         removing only the first reference if `leave_dupes` is True
        """
        changed = False
        for song in songs:
            # TODO: document the "library.masked" business
            if library.masked(song("~filename")):
                while True:
                    try:
                        self[self.index(song)] = song("~filename")
                    except ValueError:
                        break
                    else:
                        changed = True
            else:
                while song in self.songs:
                    print_d("Removing \"%s\" from playlist \"%s\"..."
                            % (song["~filename"], self.name))
                    self.songs.remove(song)
                    if leave_dupes:
                        changed = True
                        break
                else:
                    changed = True
            # Evict song from cache entirely
            try:
                del self._song_map_cache[song]
                print_d("Removed playlist cache for \"%s\"" % song["~filename"])
            except KeyError: pass
        return changed

    def has_songs(self, songs):
        # TODO(rm): consider the "library.masked" business
        some, all = False, True
        for song in songs:
            found = song in self.songs
            some = some or found
            all = all and found
            if some and not all:
                break
        return some, all

    def delete(self):
        self.clear()
        try: os.unlink(os.path.join(self.dir, self.quote(self.name)))
        except EnvironmentError: pass

    def write(self):
        basename = self.quote(self.name)
        f = file(os.path.join(self.dir, basename), "w")
        for song in self:
            try: f.write(util.fsencode(song("~filename")) + "\n")
            except TypeError: f.write(song + "\n")
        f.close()

    def format(self):
        """A markup representation of information for this playlist"""
        total_size = float(self.get("~#filesize") or 0.0)
        songs_text = (ngettext("%d song", "%d songs", len(self.songs))
                      % len(self.songs))
        # see Issue 504
        return "<b>%s</b>\n<small>%s (%s%s)</small>" % (
                util.escape(self.name),
                songs_text,
                self.get("~length", "0:00"),
                " / %s" % util.format_size(total_size) if total_size>0 else "")

    def has_duplicates(self):
        """Returns True if there are any duplicated files in this playlist"""
        unique = set()
        for s in self:
            if s in unique: return False
            else: unique.add(s)
        return True

    def shuffle(self):
        """
        Randomly shuffles this playlist, permanently.
        Currently this is unweighted
        """
        random.shuffle(self.songs)
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
