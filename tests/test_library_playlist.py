# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
from quodlibet import app
from quodlibet.formats import AudioFile
from quodlibet.library import SongFileLibrary
from quodlibet.util import connect_obj
from quodlibet.util.collection import Playlist
from tests import TestCase
from tests.test_library_libraries import FakeSong


def AFrange(*args):
    return [
        AudioFile({"~filename": f"/tmp/{i}.mp3",
                   "artist": "Foo",
                   "title": f"track-{i}"})
        for i in range(*args)]


class TPlaylistLibrary(TestCase):
    Fake = FakeSong
    Frange = staticmethod(AFrange)
    UnderlyingLibrary = SongFileLibrary

    def setUp(self):
        self.underlying = self.UnderlyingLibrary()
        # Need this for ~playlists
        app.library = self.underlying
        self.added = []
        self.changed = []
        self.removed = []

        self._sigs = [
            connect_obj(self.underlying, 'changed', list.extend, self.changed),
            connect_obj(self.underlying, 'removed', list.extend, self.removed),
        ]

        self.library = self.underlying.playlists

        # Populate for every test
        self.underlying.add(self.Frange(12))
        for song in self.underlying:
            song.sanitize()
        pl = Playlist("One", self.underlying, self.library)
        # Add last three songs to playlist
        pl.extend(list(self.underlying)[-3:])

    def tearDown(self):
        for s in self._sigs:
            self.underlying.disconnect(s)
        self.underlying.destroy()
        self.library.destroy()
        for pl in list(self.library.values()):
            pl.delete()
        app.library = None

    def test_get(self):
        key = "One"
        pl = self.library.get(key)
        assert pl.name == "One"
        assert pl.key == key
        assert len(pl.songs) == 3

        assert not self.underlying.get("Two")

    def test_keys(self):
        assert list(self.library.keys()) == ["One"]

    def test_has_key(self):
        key = self.underlying.get("/tmp/11.mp3").list("~playlists")[0]
        assert self.library.has_key(key)

    def test_misc_collection(self):
        self.failUnless(self.library.values())

    def test_items(self):
        assert len(self.library.items()) == 1

    def test_remove(self):
        self.underlying.remove(list(self.underlying.values()))
        assert self.library["One"] is not None
        assert not self.library["One"], "Should appear empty"

    def test_misc(self):
        # It shouldn't implement FileLibrary etc
        self.failIf(getattr(self.library, "filename", None))


class TPlaylistLibrarySignals(TestCase):
    def setUp(self):
        self.lib = lib = SongFileLibrary()
        self.received = []

        def listen(name, items):
            self.received.append(name)

        self._sigs = [
            connect_obj(lib, 'added', listen, 'added'),
            connect_obj(lib, 'changed', listen, 'changed'),
            connect_obj(lib, 'removed', listen, 'removed'),
        ]

        self.playlists = lib.playlists
        self._asigs = [
            connect_obj(self.playlists, 'added', listen, 'pl_added'),
            connect_obj(self.playlists, 'changed', listen, 'pl_changed'),
            connect_obj(self.playlists, 'removed', listen, 'pl_removed'),
        ]
        songs = AFrange(3)
        for song in songs:
            song.sanitize()
        self.lib.add(songs)

    def test_add_remove(self):
        pl = Playlist("only", self.lib, self.playlists)
        assert self.received == ["added", "pl_added"]
        self.received.clear()

        # Update playlist, should trigger changes in files too
        pl.extend(self.lib._contents.values())
        # Changing files then does trigger another change,
        # annoying but seems impossible to avoid if we want to save metadata, ~playlists
        assert self.received == ["pl_changed", "changed", "pl_changed"]
        self.received.clear()

        # Remove some songs and watch the playlist change
        songs = list(self.lib._contents.values())
        self.lib.remove(songs[:2])
        assert self.received == ["removed", "pl_changed", "changed"]
        self.received.clear()

        pl.delete()
        assert self.received == ["pl_removed"]

    def test_songs_changes_have_no_effect(self):
        self.received.clear()
        self.lib.changed(list(self.lib)[0:1])
        assert self.received == ["changed"]

    def tearDown(self):
        for s in self._asigs:
            self.playlists.disconnect(s)
        for s in self._sigs:
            self.lib.disconnect(s)
        self.lib.destroy()
