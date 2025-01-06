# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.library import SongLibrary
from quodlibet.library.album import AlbumLibrary
from quodlibet.library.base import Library
from quodlibet.util import connect_obj
from tests import TestCase
from tests.test_library_libraries import FakeSong, ASrange, AlbumSong


class TAlbumLibrary(TestCase):
    Fake = FakeSong
    Frange = staticmethod(ASrange)
    UnderlyingLibrary = Library

    def setUp(self):
        self.underlying = self.UnderlyingLibrary()
        self.added = []
        self.changed = []
        self.removed = []

        self._sigs = [
            connect_obj(self.underlying, "added", list.extend, self.added),
            connect_obj(self.underlying, "changed", list.extend, self.changed),
            connect_obj(self.underlying, "removed", list.extend, self.removed),
        ]

        self.library = AlbumLibrary(self.underlying)

        # Populate for every test
        self.underlying.add(self.Frange(12))

    def tearDown(self):
        for s in self._sigs:
            self.underlying.disconnect(s)
        self.underlying.destroy()
        self.library.destroy()

    def test_get(self):
        key = self.underlying.get("file_1.mp3").album_key
        self.assertEqual(self.library.get(key).title, "Album 1")
        album = self.library.get(key)
        self.assertEqual(album.key, key)
        self.assertEqual(len(album.songs), 4)

        key = self.underlying.get("file_2.mp3").album_key
        self.assertEqual(self.library.get(key).title, "Album 2")

    def test_getitem(self):
        key = self.underlying.get("file_4.mp3").album_key
        self.assertEqual(self.library[key].key, key)

    def test_keys(self):
        assert len(self.library.keys()), 3

    def test_has_key(self):
        key = self.underlying.get("file_1.mp3").album_key
        assert self.library.has_key(key)

    def test_misc_collection(self):
        assert self.library.values()

    def test_items(self):
        self.assertEqual(len(self.library.items()), 3)

    def test_items_2(self):
        albums = self.library.values()
        self.assertEqual(len(albums), 3)
        songs = self.underlying._contents.values()
        # Make sure "all the songs' albums" == "all the albums", roughly
        self.assertEqual({a.key for a in albums}, {s.album_key for s in songs})

    def test_remove(self):
        key = self.underlying.get("file_1.mp3").album_key
        songs = self.underlying._contents

        # Remove all songs in Album 1
        for i in range(1, 12, 3):
            song = songs["file_%d.mp3" % i]
            self.underlying.remove([song])

        # Album 1 is all gone...
        self.assertEqual(self.library.get(key), None)

        # ...but Album 2 is fine
        key = self.underlying.get("file_2.mp3").album_key
        album2 = self.library[key]
        self.assertEqual(album2.key, key)
        self.assertEqual(len(album2.songs), 4)

    def test_misc(self):
        # It shouldn't implement FileLibrary etc
        assert not getattr(self.library, "filename", None)


class TAlbumLibrarySignals(TestCase):
    def setUp(self):
        lib = SongLibrary()
        received = []

        def listen(name, items):
            received.append(name)

        self._sigs = [
            connect_obj(lib, "added", listen, "added"),
            connect_obj(lib, "changed", listen, "changed"),
            connect_obj(lib, "removed", listen, "removed"),
        ]

        albums = lib.albums
        self._asigs = [
            connect_obj(albums, "added", listen, "a_added"),
            connect_obj(albums, "changed", listen, "a_changed"),
            connect_obj(albums, "removed", listen, "a_removed"),
        ]

        self.lib = lib
        self.albums = albums
        self.received = received

    def test_add_one(self):
        self.lib.add([AlbumSong(1)])
        self.assertEqual(self.received, ["added", "a_added"])

    def test_add_two_same(self):
        self.lib.add([AlbumSong(1, "a1")])
        self.lib.add([AlbumSong(5, "a1")])
        self.assertEqual(self.received, ["added", "a_added", "added", "a_changed"])

    def test_remove(self):
        songs = [AlbumSong(1, "a1"), AlbumSong(2, "a1"), AlbumSong(4, "a2")]
        self.lib.add(songs)
        self.lib.remove(songs[:2])
        self.assertEqual(self.received, ["added", "a_added", "removed", "a_removed"])

    def test_change(self):
        songs = [AlbumSong(1, "a1"), AlbumSong(2, "a1"), AlbumSong(4, "a2")]
        self.lib.add(songs)
        self.lib.changed(songs)
        self.assertEqual(self.received, ["added", "a_added", "changed", "a_changed"])

    def tearDown(self):
        for s in self._asigs:
            self.albums.disconnect(s)
        for s in self._sigs:
            self.lib.disconnect(s)
        self.lib.destroy()
