# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import shutil
from pathlib import Path

import pytest
from gi.repository import Gdk, Gtk

import quodlibet.config
from quodlibet import app
from quodlibet import qltk
from quodlibet.browsers._base import BrowserError
from quodlibet.browsers.playlists import PlaylistsBrowser
from quodlibet.browsers.playlists.prefs import DEFAULT_PATTERN_TEXT
from quodlibet.browsers.playlists.util import (parse_m3u,
                                               parse_pls, _name_for)
from quodlibet.library.file import FileLibrary
from quodlibet.library.playlist import _DEFAULT_PLAYLIST_DIR, PlaylistLibrary
from quodlibet.formats import AudioFile
from quodlibet.library import SongFileLibrary
from quodlibet.library.librarians import SongLibrarian
from quodlibet.qltk.songlist import DND_QL
from quodlibet.util.collection import FileBackedPlaylist, XSPFBackedPlaylist
from quodlibet.util.path import mkdir
from senf import fsnative, fsn2uri, fsn2bytes
from tests import (TestCase, get_data_path, mkdtemp, _TEMP_DIR,
                   init_fake_app, destroy_fake_app, run_gtk_loop)
from tests.gtk_helpers import MockSelData
from tests.test_browsers_search import SONGS
from .helper import dummy_path, __, temp_filename


class ConfigSetupMixin:
    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()


class TParsePlaylistMixin:

    def test_parse_empty(self):
        with temp_filename() as name:
            with open(name) as f:
                pl = self.Parse(f, name, pl_lib=self.pl_lib)
        self.assertFalse(pl)
        pl.delete()

    def test_parse_onesong(self):
        with temp_filename() as name:
            with open(name, "wb") as af:
                target = self.prefix
                target += fsn2bytes(get_data_path("silence-44-s.ogg"), "utf-8")
                af.write(target)
            with open(name, "rb") as f:
                pl = self.Parse(f, name, pl_lib=self.pl_lib)
        self.assertEqual(len(pl), 1)
        self.assertEqual(pl[0]("title"), "Silence")
        pl.delete()

    def test_parse_onesong_uri(self):
        target = get_data_path("silence-44-s.ogg")
        target = fsn2uri(target).encode("ascii")
        target = self.prefix + target
        with temp_filename() as name:
            with open(name, "wb") as f:
                f.write(target)
            with open(name, "rb") as f:
                pl = self.Parse(f, name, pl_lib=self.pl_lib)
        self.assertEqual(len(pl), 1)
        self.assertEqual(pl[0]("title"), "Silence")
        pl.delete()


class TParseM3U(TestCase, ConfigSetupMixin, TParsePlaylistMixin):
    Parse = staticmethod(parse_m3u)
    prefix = b""

    def setUp(self):
        self.pl_lib = PlaylistLibrary(SongFileLibrary())


class TParsePLS(TestCase, ConfigSetupMixin, TParsePlaylistMixin):
    Parse = staticmethod(parse_pls)
    prefix = b"File1="

    def setUp(self):
        self.pl_lib = PlaylistLibrary(SongFileLibrary())


class TPlaylistIntegration(TestCase):
    DUPLICATES = 1
    SONG = AudioFile({
                "title": "two",
                "artist": "mu",
                "~filename": dummy_path("/dev/zero")})
    SONGS = [
        AudioFile({
                "title": "one",
                "artist": "piman",
                "~filename": dummy_path("/dev/null")}),
        SONG,
        AudioFile({
                "title": "three",
                "artist": "boris",
                "~filename": dummy_path("/bin/ls")}),
        AudioFile({
                "title": "four",
                "artist": "random",
                "album": "don't stop",
                "labelid": "65432-1",
                "~filename": dummy_path("/dev/random")}),
        SONG,
        ]

    def setUp(self):
        quodlibet.config.init()
        self.lib = quodlibet.browsers.tracks.library = SongFileLibrary()
        quodlibet.browsers.tracks.library.librarian = SongLibrarian()
        for af in self.SONGS:
            af.sanitize()
        self.lib.add(self.SONGS)
        self._dir = mkdtemp()
        self.pl = FileBackedPlaylist.new(self._dir, "Foobar",
                                         self.lib, self.lib.playlists)
        self.pl.extend(self.SONGS)

    def tearDown(self):
        self.pl.delete()
        self.lib.destroy()
        self.lib.librarian.destroy()
        quodlibet.config.quit()
        shutil.rmtree(self._dir)

    def test_remove_song(self):
        # Check: library should have one song fewer (the duplicate)
        self.assertEqual(len(self.lib),
                             len(self.SONGS) - self.DUPLICATES)
        self.assertEqual(len(self.pl), len(self.SONGS))

        # Remove an unduplicated song
        self.pl.remove_songs([self.SONGS[0]])
        self.assertEqual(len(self.pl), len(self.SONGS) - 1)

    def test_remove_duplicated_song(self):
        self.assertEqual(self.SONGS[1], self.SONGS[4])
        self.pl.remove_songs([self.SONGS[1]])
        self.assertEqual(len(self.pl), len(self.SONGS) - 2)

    def test_remove_multi_duplicated_song(self):
        self.pl.extend([self.SONG, self.SONG])
        self.assertEqual(len(self.pl), 7)
        self.pl.remove_songs([self.SONG], False)
        self.assertEqual(len(self.pl), 7 - 2 - 2)

    def test_remove_duplicated_song_leave_dupes(self):
        self.pl.remove_songs([self.SONGS[1]], True)
        self.assertEqual(len(self.pl), len(self.SONGS) - 1)

    def test_remove_no_lib(self):
        pl = FileBackedPlaylist.new(self._dir, "Foobar")
        pl.extend(self.SONGS)
        self.assertTrue(len(pl))
        pl.remove_songs(self.SONGS, False)
        self.assertFalse(len(pl))


class TPlaylistsBrowser(TestCase):
    Bar = PlaylistsBrowser

    ANOTHER_SONG = AudioFile({
        "title": "lonely",
        "artist": "new artist",
        "~filename": dummy_path("/dev/urandom")})

    ALL_SONGS = SONGS + [ANOTHER_SONG]

    def setUp(self):
        self.success = False
        # Testing locally is VERY dangerous without this...
        self.assertTrue(_TEMP_DIR in _DEFAULT_PLAYLIST_DIR or os.name == "nt",
                        msg="Failing, don't want to delete %s" % _DEFAULT_PLAYLIST_DIR)
        try:
            shutil.rmtree(_DEFAULT_PLAYLIST_DIR)
        except OSError:
            pass

        mkdir(_DEFAULT_PLAYLIST_DIR)

        init_fake_app()

        self.lib = quodlibet.browsers.playlists.library = SongFileLibrary()
        self.lib.librarian = SongLibrarian()
        for af in self.ALL_SONGS:
            af.sanitize()
        self.lib.add(self.ALL_SONGS)

        self.big = pl = FileBackedPlaylist.new(_DEFAULT_PLAYLIST_DIR, "Big",
                                               self.lib, self.lib.playlists)
        pl.extend(SONGS)
        pl.write()

        self.small = pl = XSPFBackedPlaylist.new(_DEFAULT_PLAYLIST_DIR,
                                                 "Small", self.lib, self.lib.playlists)
        pl.extend([self.ANOTHER_SONG])
        pl.write()

        PlaylistsBrowser.init(self.lib)

        self.bar = PlaylistsBrowser(self.lib, self.MockConfirmerAccepting)
        self.bar.connect("songs-selected", self._expected)
        self.bar._select_playlist(self.bar.playlists()[0])
        self.expected = None

        # Uses the declining confirmer.
        self.bar_decline = PlaylistsBrowser(self.lib, self.MockConfirmerDeclining)
        self.bar_decline.connect("songs-selected", self._expected_decline)
        self.bar_decline._select_playlist(self.bar_decline.playlists()[0])
        # Note that _do() uses self.expected, but _do() is not called by the
        # testcase for declining the prompt. Tests fail with a shared expected.
        self.expected_decline = None

    def tearDown(self):
        self.small.delete()
        self.big.delete()
        self.bar.destroy()
        self.lib.destroy()
        shutil.rmtree(_DEFAULT_PLAYLIST_DIR)
        destroy_fake_app()

    def _expected(self, bar, songs, sort):
        songs.sort()
        if self.expected is not None:
            self.assertEqual(self.expected, songs)
        self.success = True

    def _expected_decline(self, bar, songs, sort):
        songs.sort()
        if self.expected_decline is not None:
            self.assertEqual(self.expected_decline, songs)
        self.success = True

    def _do(self):
        run_gtk_loop()
        self.assertTrue(self.success or self.expected is None)

    def test_saverestore(self):
        # Flush previous signals, etc. Hmm.
        self.expected = None
        self._do()
        self.expected = [SONGS[0]]
        self.bar.filter_text("title = %s" % SONGS[0]["title"])
        self.bar._select_playlist(self.bar.playlists()[0])
        self.expected = [SONGS[0]]
        self._do()
        self.bar.save()
        self.bar.filter_text("")
        self.expected = sorted(SONGS)
        self._do()
        self.bar.restore()
        self.bar.activate()
        self.expected = [SONGS[0]]
        self._do()

    def test_active_filter_playlists(self):
        self.bar._select_playlist(self.bar.playlists()[1])

        # Second playlist should not have any of `SONGS`
        self.assertFalse(self.bar.active_filter(SONGS[0]))

        # But it should have `ANOTHER_SONG`
        self.assertTrue(self.bar.active_filter(self.ANOTHER_SONG),
                        msg="Couldn't find song from second playlist")

        # ... and setting a reasonable filter on that song should match still
        self.bar.filter_text("lonely")
        self.assertTrue(self.bar.active_filter(self.ANOTHER_SONG),
                        msg="Couldn't find song from second playlist with "
                            "filter of 'lonely'")

        # ...unless it doesn't match that song
        self.bar.filter_text("piman")
        self.assertFalse(self.bar.active_filter(self.ANOTHER_SONG),
                         msg="Shouldn't have matched 'piman' on second list")

    def test_rename(self):
        self.assertEqual(self.bar.playlists()[1], self.small)
        assert self.bar._rename(0, "zBig")
        self.assertEqual(self.bar.playlists()[0], self.small)
        self.assertEqual(self.bar.playlists()[1].name, "zBig")

    def test_rename_empty(self):
        assert not self.bar._rename(0, "", show_error=False)

    def test_default_display_pattern(self):
        pattern_text = self.bar.display_pattern_text
        self.assertEqual(pattern_text, DEFAULT_PATTERN_TEXT)
        self.assertTrue("<~name>" in pattern_text)

    def test_drag_data_get(self):
        b = self.bar
        song = AudioFile()
        song["~filename"] = fsnative("foo")
        sel = MockSelData()
        qltk.selection_set_songs(sel, [song])
        b._drag_data_get(None, None, sel, DND_QL, None)

    def test_playlist_drag_data_extend_accept(self):
        b = self.bar
        song1 = AudioFile()
        song2 = AudioFile()
        song3 = AudioFile()
        song1["~filename"] = fsnative("foo1")
        song2["~filename"] = fsnative("foo2")
        song3["~filename"] = fsnative("foo3")
        sel = MockSelData()
        qltk.selection_set_songs(sel, [song1, song2, song3])
        filenames = qltk.selection_get_filenames(sel)

        first_pl = b.playlists()[0]
        original_length = len(first_pl)
        # This is usually called by __drag_data_received, but that is heavily
        # dependent on gtk-views, so is more conveniently called manually.
        b._add_drag_data_tracks_to_playlist(first_pl, filenames)
        self.assertEqual(len(first_pl), original_length + 3)

    def test_playlist_drag_data_extend_decline(self):
        b = self.bar_decline
        song1 = AudioFile()
        song2 = AudioFile()
        song3 = AudioFile()
        song1["~filename"] = fsnative("foo1")
        song2["~filename"] = fsnative("foo2")
        song3["~filename"] = fsnative("foo3")
        sel = MockSelData()
        qltk.selection_set_songs(sel, [song1, song2, song3])
        filenames = qltk.selection_get_filenames(sel)

        first_pl = b.playlists()[0]
        original_length = len(first_pl)
        b._add_drag_data_tracks_to_playlist(first_pl, filenames)
        self.assertEqual(len(first_pl), original_length)

    def test_songs_deletion(self):
        b = self.bar
        self._fake_browser_pack(b)
        event = self.a_delete_event()
        # This is selected in setUp()
        first_pl = b.playlists()[0]
        app.window.songlist.set_songs(first_pl)
        app.window.songlist.select_by_func(lambda x: True,
                                           scroll=False, one=True)
        original_length = len(first_pl)
        ret = b.key_pressed(event)
        self.assertTrue(ret, msg="Didn't simulate a delete keypress")
        self.assertEqual(len(first_pl), original_length - 1)

    def test_playlist_deletion_ACCEPT(self):
        b = self.bar
        orig_length = len(b.playlists())
        event = self.a_delete_event()
        first_pl = b.playlists()[0]
        second_pl = b.playlists()[1]
        b._select_playlist(first_pl)

        ret = b._PlaylistsBrowser__key_pressed(b, event)
        self.assertTrue(ret, msg="Didn't simulate a delete keypress")
        self.assertEqual(len(b.playlists()), orig_length - 1)
        self.assertEqual(b.playlists()[0], second_pl)

    def test_playlist_deletion_CANCEL(self):
        b = self.bar_decline
        orig_length = len(b.playlists())
        event = self.a_delete_event()
        first_pl = b.playlists()[0]
        second_pl = b.playlists()[1]
        b._select_playlist(first_pl)

        ret = b._PlaylistsBrowser__key_pressed(b, event)
        self.assertTrue(ret, msg="Didn't simulate a delete keypress")
        self.assertEqual(len(b.playlists()), orig_length)
        self.assertEqual(b.playlists()[0], first_pl)
        self.assertEqual(b.playlists()[1], second_pl)

    def test_import(self):
        def fns(songs):
            return [song("~filename") for song in songs]
        pl_lib = self.bar.pl_lib
        assert len(self.bar.playlists()) == 2, "Should start with two playlists"
        assert len(pl_lib) == 2, f"Started with {pl_lib.keys()}"

        pl_name = "_€3 œufs à Noël"
        pl_path = Path(_TEMP_DIR) / (pl_name + ".m3u")
        with open(pl_path, "wb") as f:
            for fn in fns(SONGS):
                f.write(fsn2bytes(fn, "utf-8") + b"\n")
        pls_added, songs_added = self.bar._import_playlists([str(pl_path)])
        assert pls_added == 1, f"Failed to add {pl_path}"
        assert len(self.bar.songs_lib) == len(self.ALL_SONGS)
        assert songs_added == 0, "Why did we add existing songs?"
        assert len(pl_lib) == 3, f"Got PLs: \n{', '.join(str(pl) for pl in pl_lib)}"
        pls = self.bar.playlists()
        assert len(pls) == 3, f"Got PL rows: {', '.join(str(pl) for pl in pls)}"
        # Leading underscore makes it always the last entry
        imported = pls[-1]
        self.assertEqual(fns(imported.songs), fns(SONGS))

    def test_no_pl_lib(self):
        """Probably not possible in real runtime situations"""
        with pytest.raises(BrowserError):
            assert PlaylistsBrowser(FileLibrary("no-playlists"))

    @staticmethod
    def a_delete_event():
        ev = Gdk.Event()
        ev.type = Gdk.EventType.KEY_PRESS
        ev.keyval, accel_mod = Gtk.accelerator_parse("Delete")
        ev.state = Gtk.accelerator_get_default_mod_mask() & accel_mod
        return ev

    @staticmethod
    def _fake_browser_pack(b):
        app.window.get_child().pack_start(b, True, True, 0)

    class MockConfirmerAccepting:

        RESPONSE_INVOKE = Gtk.ResponseType.YES

        def __init__(self, *args):
            pass

        def run(self, *args):
            return self.RESPONSE_INVOKE

    class MockConfirmerDeclining:

        RESPONSE_INVOKE = Gtk.ResponseType.YES

        def __init__(self, *args):
            pass

        def run(self, *args):
            return Gtk.ResponseType.CANCEL


class TPlaylistUtils(TestCase):

    def test_naming(self):
        self.assertEqual(_name_for("/foo/bar.m3u"), "bar")
        self.assertEqual(_name_for("/foo/Will.I.Am.m3u"), "Will.I.Am")

    def test_naming_default(self):
        self.assertEqual(_name_for(""), __("New Playlist"))
