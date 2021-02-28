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
    songs = [
        AudioFile({"~filename": f"/tmp/{i}.mp3",
                   "artist": "Foo",
                   "title": f"track-{i}"})
        for i in range(*args)]
    # Need a mountpoint, or everything goes wrong...
    for song in songs:
        song.sanitize()
    return songs


PL_NAME = "The Only"


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

        for song in self.underlying:
            song.sanitize()
        # Populate for every test
        self.underlying.add(self.Frange(12))
        pl = Playlist(PL_NAME, self.underlying, self.library)
        # Add last three songs to playlist
        pl.extend(list(sorted(self.underlying))[-3:])
        assert len(pl) == 3, "Should have only the three songs just added"
        diff = set(self.underlying) - set(pl)
        assert all(song in self.underlying for song in pl), f"Missing from lib: {diff}"
        pl.finalize()

    def tearDown(self):
        for pl in list(self.library.values()):
            pl.delete()
        for s in self._sigs:
            self.underlying.disconnect(s)
        self.underlying.destroy()
        # Don't destroy self.library, it's a reference which is gone
        app.library = None

    def test_get(self):
        pl = self.library.get(PL_NAME)
        assert pl.name == PL_NAME
        assert pl.key == PL_NAME
        assert len(pl.songs) == 3

        assert not self.underlying.get("Another")

    def test_keys(self):
        assert list(self.library.keys()) == [PL_NAME]

    def test_has_key(self):
        last_song = list(self.underlying)[-1]
        key = last_song.list("~playlists")[0]
        assert self.library.has_key(key)

    def test_misc_collection(self):
        self.failUnless(self.library.values())

    def test_items(self):
        assert len(self.library.items()) == 1

    def test_remove_songs(self):
        pl = self.library[PL_NAME]
        all_contents = list(self.underlying.values())
        assert all(song in self.underlying for song in pl), "Not all songs are in lib"
        removed = self.underlying.remove(all_contents)
        assert set(removed) == set(all_contents), "Not everything removed from lib"
        assert not pl, f"PL should be empty, has: {list(pl)}"

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
        assert self.received == ["removed", "pl_changed", "changed", "pl_changed"]
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
