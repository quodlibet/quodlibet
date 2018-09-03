# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re

from quodlibet import _
from quodlibet import util
from quodlibet.qltk.models import ObjectStore
from quodlibet.util.collection import Collection
from quodlibet.compat import iteritems


class BaseEntry(Collection):

    def __init__(self, key=None, songs=None):
        super(BaseEntry, self).__init__()

        self.songs = set(songs or [])
        self.key = key # not used for sorting!
        self.sort = tuple()

    def all_have(self, tag, value):
        """Check if all songs have tag `tag` set to `value`"""

        if tag[:2] == "~#" and "~" not in tag[2:]:
            for song in self.songs:
                if song(tag) != value:
                    return False
        else:
            for song in self.songs:
                if value not in song.list(tag):
                    return False
        return True

    def get_count_text(self, config):
        raise NotImplementedError

    def get_text(self, config):
        """Returns (is_markup, text)"""

        raise NotImplementedError

    def contains_text(self, text):
        """Used for the inline search"""

        raise NotImplementedError


class SongsEntry(BaseEntry):

    def __init__(self, key, sort, songs=None):
        super(SongsEntry, self).__init__(key, songs)

        self.sort = sort # value used for sorting

    def get_count_text(self, config):
        return config.format_display(self)

    def get_text(self, config):
        if config.has_markup:
            return True, self.key
        else:
            return False, self.key

    def contains_text(self, text):
        return text.lower() in self.key.lower()

    def contains_song(self, song):
        return song in self.songs

    def __repr__(self):
        return "<%s key=%r songs=%d>" % (
            type(self).__name__, self.key, len(self.songs))


class UnknownEntry(SongsEntry):

    def __init__(self, songs=None):
        super(UnknownEntry, self).__init__("", tuple(), songs)

    def get_text(self, config):
        return True, "<b>%s</b>" % _("Unknown")

    def contains_text(self, text):
        return False

    def __repr__(self):
        return "<%s songs=%d>" % (type(self).__name__, len(self.songs))


class AllEntry(BaseEntry):

    def __init__(self):
        super(AllEntry, self).__init__()

    def get_count_text(self, config):
        return u""

    def get_text(self, config):
        return True, "<b>%s</b>" % _("All")

    def contains_text(self, text):
        return False

    def contains_song(self, song):
        return False

    def __repr__(self):
        return "<%s>" % (type(self).__name__,)


class PaneModel(ObjectStore):

    def __init__(self, pattern_config):
        super(PaneModel, self).__init__()
        self.__sort_cache = {} # text to sort text cache
        self.__key_cache = {} # song to key cache
        self.config = pattern_config

    def get_format_keys(self, song):
        try:
            return self.__key_cache[song]
        except KeyError:
            # We filter out empty values, so Unknown can be ""
            self.__key_cache[song] = list(filter(
                lambda v: v[0], self.config.format(song)))
            return self.__key_cache[song]

    def __human_sort_key(self, text, reg=re.compile('<.*?>')):
        try:
            return self.__sort_cache[text], text
        except KeyError:
            # remove the markup so it doesn't affect the sort order
            if self.config.has_markup:
                text_stripped = reg.sub("", text)
            else:
                text_stripped = text
            self.__sort_cache[text] = util.human_sort_key(text_stripped)
            return self.__sort_cache[text], text

    def get_songs(self, paths):
        """Get all songs for the given paths (from a selection e.g.)"""

        s = set()
        if not paths:
            return s

        first_path = paths[0]
        if isinstance(self[first_path][0], AllEntry):
            for entry in self.itervalues():
                s.update(entry.songs)
        else:
            for path in paths:
                s.update(self[path][0].songs)

        return s

    def get_keys(self, paths):
        return {self[p][0].key for p in paths}

    def remove_songs(self, songs, remove_if_empty):
        """Remove all songs from the entries.

        If remove_if_empty == True, entries with no songs will be removed.
        """

        songs = set(songs)

        for song in songs:
            if song in self.__key_cache:
                del self.__key_cache[song]

        to_remove = []
        for iter_, entry in self.iterrows():
            if isinstance(entry, AllEntry):
                continue
            entry.songs -= songs
            entry.finalize()
            self.row_changed(self.get_path(iter_), iter_)
            if not entry.songs:
                to_remove.append(iter_)

        if not remove_if_empty:
            return

        # remove from cache and the model
        for iter_ in to_remove:
            try:
                key = self.get_value(iter_).key
                del(self.__sort_cache[key])
            except KeyError:
                pass
            self.remove(iter_)

        if len(self) == 1 and isinstance(self[0][0], AllEntry):
            # only All is left.. clear everything
            self.clear()
        elif to_remove and len(self) == 2:
            # Only one entry + All -> remove All
            self.remove(self.get_iter_first())

    def add_songs(self, songs):
        """Add new songs to the list, creating new rows"""

        collection = {}
        unknown = UnknownEntry()
        human_sort = self.__human_sort_key
        for song in songs:
            items = self.get_format_keys(song)
            if not items:
                unknown.songs.add(song)
            for key, sort in items:
                if key in collection:
                    if sort and not collection[key][2]: # first actual sort key
                        hsort = human_sort(sort)
                        collection[key][0].sort = hsort
                        collection[key] = (collection[key][0], hsort, True)
                    collection[key][0].songs.add(song)
                else: # first key sets up sorting
                    hsort = human_sort(sort)
                    entry = SongsEntry(key, hsort)
                    collection[key] = (entry, hsort, bool(sort))
                    entry.songs.add(song)

        items = sorted(iteritems(collection),
                       key=lambda s: s[1][1],
                       reverse=True)

        # fast path
        if not len(self):
            if unknown.songs:
                self.insert(0, [unknown])
            entries = []
            for key, (val, sort_key, srtp) in items:
                entries.append(val)
            self.insert_many(0, reversed(entries))
            if len(self) > 1:
                self.insert(0, [AllEntry()])
            return

        # insert all new songs
        key = None
        val = None
        sort_key = None

        for iter_, entry in self.iterrows():
            if not isinstance(entry, SongsEntry):
                continue

            if key is None:
                if not items:
                    break
                key, (val, sort_key, srtp) = items.pop(-1)

            if key == entry.key: # Display strings the same
                entry.songs |= val.songs
                entry.finalize()
                self.row_changed(self.get_path(iter_), iter_)
                key = None
            elif sort_key < entry.sort:
                self.insert_before(iter_, row=[val])
                key = None

        # the last one failed, add it again
        if key:
            items.append((key, (val, sort_key, srtp)))

        # insert the left over songs
        if items:
            entries = []
            for key, (val, srt, srtp) in items:
                entries.append(val)
            if isinstance(self[-1][0], UnknownEntry):
                self.insert_many(len(self) - 1, entries)
            else:
                self.append_many(entries)

        # check if All needs to be inserted
        if len(self) > 1 and not isinstance(self[0][0], AllEntry):
            self.insert(0, [AllEntry()])

        # check if Unknown needs to be inserted or updated
        if unknown.songs:
            last_row = self[-1]
            entry = last_row[0]
            if isinstance(entry, UnknownEntry):
                entry.songs |= unknown.songs
                entry.finalize()
                self.row_changed(last_row.path, last_row.iter)
            else:
                self.append(row=[unknown])

    def matches(self, paths, song):
        """If the song is included in the selection defined by the paths.

        paths has to be sorted.
        """

        if not paths:
            return False

        # All included
        if isinstance(self[paths[0]][0], AllEntry):
            return True

        keys = self.get_format_keys(song)

        # empty key -> unknown
        if not keys and isinstance(self[paths[-1]][0], UnknownEntry):
            return True

        for path in paths:
            entry = self.get_value(self.get_iter(path))
            for key in keys:
                if entry.key == (key[0] if isinstance(key, tuple) else key):
                    return True

        return False

    def list(self, tag):
        tags = self.config.tags

        # fast path, use the keys since they are unique and only depend
        # on the tag in question.
        if tag in tags and len(tags) == 1:
            return {r.key for r in self.itervalues()
                    if not isinstance(r, AllEntry)}

        # For patterns/tied tags we have to make sure that filtering for
        # that key will return only songs that all have the specified value
        values = set()
        for entry in self.itervalues():
            if isinstance(entry, AllEntry):
                continue

            if not entry.key:
                # add unknown
                values.add("")
            else:
                for value in entry.list(tag):
                    if value not in values and entry.all_have(tag, value):
                        values.add(value)

        return values

    def get_keys_by_tag(self, tag, values):
        """List of keys for entries where all songs contain a tag
        with at least one value from values.
        """

        tags = self.config.tags

        # Like with self.list we can select all matching keys if the tag
        # is our only tag
        if len(tags) == 1 and tag in tags:
            return [e.key for e in self.itervalues() if e.key in values]

        keys = []
        for entry in self.itervalues():
            if isinstance(entry, SongsEntry):
                for value in values:
                    if entry.all_have(tag, value):
                        keys.append(entry.key)
                        break

        # add unknown
        if "" in values and isinstance(self[-1][0], UnknownEntry):
            keys.append("")

        return keys
