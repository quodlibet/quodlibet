# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman
#                2012 Nick Boultbee
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
import re

from quodlibet import const
from quodlibet import util
from quodlibet import config

from quodlibet.util.uri import URI
from quodlibet.util import HashableDict
from quodlibet.util import human_sort_key as human
from quodlibet.util.tags import STANDARD_TAGS as USEFUL_TAGS
from quodlibet.util.tags import MACHINE_TAGS

MIGRATE = frozenset(("~#playcount ~#laststarted ~#lastplayed ~#added "
           "~#skipcount ~#rating ~bookmark").split())

PEOPLE = ("albumartist artist author composer ~performers originalartist "
          "lyricist arranger conductor").split()

TAG_TO_SORT = {
    "artist": "artistsort",
    "album": "albumsort",
    "albumartist": "albumartistsort",
    "performersort": "performersort",
    "~performerssort": "~performerssort"
    }

INTERN_NUM_DEFAULT = frozenset("~#lastplayed ~#laststarted ~#playcount "
    "~#skipcount ~#length ~#bitrate ~#filesize".split())

SORT_TO_TAG = dict([(v, k) for (k, v) in TAG_TO_SORT.iteritems()])

PEOPLE_SORT = [TAG_TO_SORT.get(k, k) for k in PEOPLE]

FILESYSTEM_TAGS = "~filename ~basename ~dirname".split()

# tags that should alone identify an album, ordered by descending preference
UNIQUE_ALBUM_IDENTIFIERS = ["musicbrainz_albumid", "labelid"]

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
    mimes = []

    @util.cached_property
    def __song_key(self):
        return (self("~#disc"), self("~#track"),
            human(self("artistsort")),
            self.get("musicbrainz_artistid", ""),
            human(self.get("title", "")),
            self.get("~filename"))

    @util.cached_property
    def album_key(self):
        return (human(self("albumsort", "")),
                self.get("album_grouping_key") or self.get("labelid") or
                self.get("musicbrainz_albumid") or "")

    @util.cached_property
    def sort_key(self):
        return [self.album_key, self.__song_key]

    @staticmethod
    def sort_by_func(tag):
        """Returns a fast sort function for a specific tag (or pattern).
        Some keys are already in the sort cache, so we can use them."""
        def artist_sort(song):
            return (song.sort_key[1][2])

        if callable(tag):
            return lambda song: human(tag(song))
        elif tag == "artistsort":
            return artist_sort
        elif tag in FILESYSTEM_TAGS:
            return lambda song: util.fsdecode(song(tag), note=False)
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
        dict.__setitem__(self, key, value)

        if not self.__dict__:
            return
        pop = self.__dict__.pop
        pop("album_key", None)
        pop("sort_key", None)
        pop("__song_key", None)

    def __delitem__(self, key):
        dict.__delitem__(self, key)

        if not self.__dict__:
            return
        pop = self.__dict__.pop
        pop("album_key", None)
        pop("sort_key", None)
        pop("__song_key", None)

    key = property(lambda self: self["~filename"])
    mountpoint = property(lambda self: self["~mountpoint"])

    def _album_id_values(self, use_artist=False):
        """Returns a "best attempt" conjunction (=AND) of album identifiers

        Tries the (probably) most specific keys first, then gets less accurate
        but more verbose (eg artist="foo" AND album="bar").
        
        if use_artist is True, the track artist will also be used as a key if
        necessary. This breaks compilations, but does well for overloaded
        album names (eg "Greatest Hits")
        """
        ret = HashableDict()
        for key in UNIQUE_ALBUM_IDENTIFIERS:
            val = self.get(key)
            if val: 
                ret[key] = val
                break
        if not ret and "album" in self:
            # Add helpful identifiers where they exist
            for key in ["album", "albumartist", "album_grouping_key"]:
                val = self.get(key)
                if val: ret[key] = val
            if use_artist and "albumartist" not in ret and "artist" in self: 
                ret["artist"] = self.get("artist")
        return ret

    album_id_values = property(_album_id_values)

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

    def __ne__(self, other):
        return self is not other

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
                # FIXME: decode ~filename etc.
                if not isinstance(default, basestring): return default
                return connector.join(
                    filter(None,
                    map(lambda x: isinstance(x, basestring) and x or str(x),
                    map(lambda x: (isinstance(x, float) and "%.2f" % x) or x,
                    map(self.__call__, util.tagsplit("~" + key)))))) or default
            elif key == "#track":
                try: return int(self["tracknumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key == "#disc":
                try: return int(self["discnumber"].split("/")[0])
                except (ValueError, TypeError, KeyError): return default
            elif key == "length":
                length = self.get("~#length")
                if length is None: return default
                else: return util.format_time(length)
            elif key == "#rating":
                return dict.get(self, "~" + key, const.DEFAULT_RATING)
            elif key == "rating":
                return util.format_rating(self("~#rating"))
            elif key == "people":
                join = "\n".join
                people = filter(None, map(self.__call__, PEOPLE))
                if not people: return default
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
            elif key == "performers" or key == "performer":
                performers = {}
                for key in self.keys():
                    if key.startswith("performer:"):
                        role = key.split(":", 1)[1]
                        for value in self.list(key):
                            try:
                                performers[str(value)]
                            except:
                                performers[str(value)] = []
                            performers[str(value)].append(util.title(role))
                values = []
                if len(performers) > 0:
                    for performer in performers:
                        roles = ''
                        i = 0
                        for role in performers[performer]:
                            if i > 0:
                                roles += ', '
                            roles += role
                            i += 1
                        values.append("%s (%s)" % (performer, roles))
                values.extend(self.list("performer"))
                if not values: return default
                return "\n".join(values)
            elif key == "performerssort" or key == "performersort":
                values = []
                for key in self.keys():
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
            elif key == "originalyear":
                return self.get("originaldate", default)[:4]
            elif key == "#originalyear":
                try: return int(self.get("originaldate", default)[:4])
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
            elif key == "playlists":
                # See Issue 876
                # Avoid circular references from formats/__init__.py
                from quodlibet.util.collection import Playlist
                try:
                    start = time.time()
                    playlists = Playlist.playlists_featuring(self)
                    import random
                    if not random.randint(0, 1000):
                        print_d("A sample song('~playlists') call: took %d μs "
                                % (1E6 * (time.time() - start)))
                    return "\n".join([s.name for s in playlists])
                except KeyError:
                    return default
            elif key.startswith("#replaygain_"):
                try:
                    val = self.get(key[1:], default)
                    return round(float(val.split(" ")[0]), 2)
                except (ValueError, TypeError, AttributeError): return default
            elif key[:1] == "#":
                key = "~" + key
                if key in self: self[key]
                elif key in INTERN_NUM_DEFAULT:
                    return dict.get(self, key, 0)
                else:
                    try: val = self[key[2:]]
                    except KeyError: return default
                    try: return int(val)
                    except ValueError:
                        try: return float(val)
                        except ValueError: return default
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
        os.path.join(util.expanduser("~/.lyrics"),
                     (self.comma("lyricist") or self.comma("artist")).replace('/', '')[:128],
                     self.comma("title").replace('/', '')[:128] + '.lyric')))

    def comma(self, key):
        """Get all values of a tag, separated by commas. Synthetic
        tags are supported, but will be slower. If the value is
        numeric, that is returned rather than a list."""

        if "~" in key or key == "title": v = self(key, u"")
        else: v = self.get(key, u"")
        if isinstance(v, (int, long, float)): return v
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

    def list_separate(self, key, connector=" - "):
        """Similar to list, but will return a list of all combinations
        for tied tags instead of one comma separated string"""
        if key[:1] == "~" and "~" in key[1:]:
            vals = \
                filter(None,
                map(lambda x: isinstance(x, basestring) and x or str(x),
                map(lambda x: (isinstance(x, float) and "%.2f" % x) or x,
                (self(tag) for tag in util.tagsplit(key)))))
            vals = (val.split("\n") for val in vals)
            r = [[]]
            for x in vals:
                r = [ i + [y] for y in x for i in r ]
            return map(connector.join, r)
        else:
            return self.list(key)

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
                      and k.encode("ascii", "replace") == k
                      and os.access(self["~filename"], os.W_OK))

    def rename(self, newname):
        """Rename a file. Errors are not handled. This shouldn't be used
        directly; use library.rename instead."""

        if os.path.isabs(newname): util.mkdir(os.path.dirname(newname))
        else: newname = os.path.join(self('~dirname'), newname)
        if not os.path.exists(newname):
            shutil.move(self['~filename'], newname)
        elif os.path.realpath(newname) != self['~filename']:
            raise ValueError
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
        """Fill in metadata defaults. Find ~mountpoint, ~#mtime, ~#filesize
        and ~#added. Check for null bytes in tags."""

        # Replace nulls with newlines, trimming zero-length segments
        for key, val in self.items():
            if isinstance(val, basestring) and '\0' in val:
                self[key] = '\n'.join(filter(lambda s: s, val.split('\0')))
            # Remove unnecessary defaults
            if key in INTERN_NUM_DEFAULT and val == 0:
                del self[key]

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
        self.setdefault("~#added", int(time.time()))

        # For efficiency, do a single stat here. See Issue 504
        try:
            stat = os.stat(self['~filename'])
            self["~#mtime"] = stat.st_mtime
            self["~#filesize"] = stat.st_size

            # Issue 342. This is a horrible approximation (due to headers)
            # ...but on FLACs, the most common case, this should be close enough
            if "~#bitrate" not in self:
                try:
                    # kbps = bytes * 8 / seconds / 1000
                    self["~#bitrate"] = int(stat.st_size /
                        (self["~#length"] * (1000/8)))
                except (KeyError, ZeroDivisionError): pass
        except OSError:
            self["~#mtime"] = 0

    def to_dump(self):
        """A string of 'key=value' lines, similar to vorbiscomment output."""
        s = []
        for k in self.keys():
            k = str(k)
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
        for k in (INTERN_NUM_DEFAULT - set(self.keys())):
            s.append("%s=%d" % (k, self.get(k, 0)))
        if "~#rating" not in self:
            s.append("~#rating=%f" % self("~#rating"))
        s.append("~format=%s" % self.format)
        s.append("")
        return "\n".join(s)

    def from_dump(self, text):
        """Parses the text created with to_dump and adds the found tags."""
        for line in text.split("\n"):
            if not line: continue
            parts = line.split("=")
            key = parts[0]
            val = "=".join(parts[1:])
            if key == "~format":
                pass
            elif key.startswith("~#"):
                try: self.add(key, int(val))
                except ValueError:
                    try: self.add(key, float(val))
                    except ValueError: pass
            else:
                self.add(key, val)

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

    # These should remain outside the loop below for performance reasons
    __cover_subdirs = frozenset(
        ["scan", "scans", "images", "covers", "artwork"])
    __cover_exts = frozenset(["jpg", "jpeg", "png", "gif"])

    __cover_positive_words = ["front", "cover", "frontcover", "jacket",
            "folder", "albumart", "edited"]
    __cover_positive_regexes = frozenset(
            map(lambda s:re.compile(r'(\b|_)' + s + r'(\b|_)'),
            __cover_positive_words))
    __cover_negative_regexes = frozenset(
            map(lambda s:re.compile(r'(\b|_|)' + s + r'(\b|_)'),
            ["back", "inlay", "inset", "inside"]))

    def find_cover(self):
        """Return a file-like containing cover image data, or None if
        no cover is available."""
        if not self.is_file: return

        # If preferred, check for picture stored in the metadata...
        if (config.getboolean("albumart", "prefer_embedded") and
                "~picture" in self):
            print_d("Preferring embedded art for %s" % self("~filename"))
            return self.get_format_cover()

        base = self('~dirname')
        images = []

        # Issue 374: Specify artwork filename
        if config.getboolean("albumart", "force_filename"):
            path = os.path.join(base, config.get("albumart", "filename"))
            if os.path.isfile(path):
                images = [(100, path)]
        else:
            get_ext = lambda s: os.path.splitext(s)[1].lstrip('.')

            entries = []
            try: entries = os.listdir(base)
            except EnvironmentError: pass

            fns = []
            for entry in entries:
                lentry = entry.lower()
                if get_ext(lentry) in self.__cover_exts:
                    fns.append((None, entry))
                if lentry in self.__cover_subdirs:
                    subdir = os.path.join(base, entry)
                    sub_entries = []
                    try: sub_entries = os.listdir(subdir)
                    except EnvironmentError: pass
                    for sub_entry in sub_entries:
                        lsub_entry = sub_entry.lower()
                        if get_ext(lsub_entry) in self.__cover_exts:
                            fns.append((entry, sub_entry))

            for sub, fn in fns:
                score = 0
                lfn = fn.lower()
                # check for the album label number
                if "labelid" in self and self["labelid"].lower() in lfn:
                    score += 20

                # Track-related keywords
                keywords =  [k.lower().strip() for k in [self("artist"),
                             self("albumartist"), self("album")] if len(k) > 1]
                score += 2 * sum(map(lfn.__contains__, keywords))

                # Generic keywords
                score += 3 * sum(r.search(lfn) is not None
                                 for r in self.__cover_positive_regexes)

                negs = sum(r.search(lfn) is not None
                           for r in self.__cover_negative_regexes)
                score -= 2 * negs
                #print("[%s - %s]: Album art \"%s\" scores %d (%s neg)." % (
                #        self("artist"), self("title"), fn, score, negs))
                if score > 0:
                    if sub is not None:
                        fn = os.path.join(sub, fn)
                    images.append((score, os.path.join(base, fn)))
            images.sort(reverse=True)

        for score, path in images:
            # could be a directory
            if not os.path.isfile(path):
                continue
            try: return file(path, "rb")
            except IOError: print_w(_("Failed reading album art \"%s\"") % path)

        if "~picture" in self:
            # Otherwise, we might have a picture stored in the metadata...
            return self.get_format_cover()

        return None

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
                scale = 10.**(db / 20)
                if scale * peak > 1:
                    scale = 1.0 / peak # don't clip
                return min(15, scale)
        else:
            return min(15, 10.**((fallback_gain+pre_amp_gain) / 20))

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
