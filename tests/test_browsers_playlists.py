# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gdk, Gtk
from senf import fsnative, fsn2uri, fsn2bytes, text2fsn

from quodlibet import app
from quodlibet import qltk
from quodlibet.browsers.playlists.prefs import DEFAULT_PATTERN_TEXT
from quodlibet.browsers.playlists.util import PLAYLISTS, parse_m3u, \
    parse_pls, _name_for
from quodlibet.qltk.songlist import DND_QL
from quodlibet.util.collection import FileBackedPlaylist
from tests import TestCase, get_data_path, mkdtemp, _TEMP_DIR, \
    init_fake_app, destroy_fake_app
from tests.gtk_helpers import MockSelData
from .helper import dummy_path, __, temp_filename

import os
import shutil

from quodlibet.browsers.playlists import PlaylistsBrowser
from quodlibet.library import SongFileLibrary
import quodlibet.config
from quodlibet.formats import AudioFile
from quodlibet.util.path import mkdir
from quodlibet.library.librarians import SongLibrarian
from quodlibet.library.libraries import FileLibrary
from tests.test_browsers_search import SONGS


class ConfigSetupMixin(object):
    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()


class TParsePlaylistMixin(object):

    def test_parse_empty(self):
        with temp_filename() as name:
            with open(name) as f:
                pl = self.Parse(f, name)
        self.failIf(pl)
        pl.delete()

    def test_parse_onesong(self):
        with temp_filename() as name:
            with open(name, "wb") as af:
                target = self.prefix
                target += fsn2bytes(get_data_path("silence-44-s.ogg"), "utf-8")
                af.write(target)
            with open(name, "rb") as f:
                pl = self.Parse(f, name)
        self.failUnlessEqual(len(pl), 1)
        self.failUnlessEqual(pl[0]("title"), "Silence")
        pl.delete()

    def test_parse_onesong_uri(self):
        target = get_data_path("silence-44-s.ogg")
        target = fsn2uri(target).encode("ascii")
        target = self.prefix + target
        with temp_filename() as name:
            with open(name, "wb") as f:
                f.write(target)
            with open(name, "rb") as f:
                pl = self.Parse(f, name)
        self.failUnlessEqual(len(pl), 1)
        self.failUnlessEqual(pl[0]("title"), "Silence")
        pl.delete()


class TParseM3U(TestCase, ConfigSetupMixin, TParsePlaylistMixin):
    Parse = staticmethod(parse_m3u)
    prefix = b""


class TParsePLS(TestCase, ConfigSetupMixin, TParsePlaylistMixin):
    Parse = staticmethod(parse_pls)
    prefix = b"File1="


class TPlaylistIntegration(TestCase):
    DUPLICATES = 1
    SONG = AudioFile({
                "title": "two",
                "artist": "mu",
                "~filename": dummy_path(u"/dev/zero")})
    SONGS = [
        AudioFile({
                "title": "one",
                "artist": "piman",
                "~filename": dummy_path(u"/dev/null")}),
        SONG,
        AudioFile({
                "title": "three",
                "artist": "boris",
                "~filename": dummy_path(u"/bin/ls")}),
        AudioFile({
                "title": "four",
                "artist": "random",
                "album": "don't stop",
                "labelid": "65432-1",
                "~filename": dummy_path(u"/dev/random")}),
        SONG,
        ]

    def setUp(self):
        quodlibet.config.init()
        self.lib = quodlibet.browsers.tracks.library = FileLibrary()
        quodlibet.browsers.tracks.library.librarian = SongLibrarian()
        for af in self.SONGS:
            af.sanitize()
        self.lib.add(self.SONGS)
        self._dir = mkdtemp()
        self.pl = FileBackedPlaylist.new(self._dir, "Foobar", self.lib)
        self.pl.extend(self.SONGS)

    def tearDown(self):
        self.pl.delete()
        self.lib.destroy()
        self.lib.librarian.destroy()
        quodlibet.config.quit()
        shutil.rmtree(self._dir)

    def test_remove_song(self):
        # Check: library should have one song fewer (the duplicate)
        self.failUnlessEqual(len(self.lib),
                             len(self.SONGS) - self.DUPLICATES)
        self.failUnlessEqual(len(self.pl), len(self.SONGS))

        # Remove an unduplicated song
        self.pl.remove_songs([self.SONGS[0]])
        self.failUnlessEqual(len(self.pl), len(self.SONGS) - 1)

    def test_remove_duplicated_song(self):
        self.failUnlessEqual(self.SONGS[1], self.SONGS[4])
        self.pl.remove_songs([self.SONGS[1]])
        self.failUnlessEqual(len(self.pl), len(self.SONGS) - 2)

    def test_remove_multi_duplicated_song(self):
        self.pl.extend([self.SONG, self.SONG])
        self.failUnlessEqual(len(self.pl), 7)
        self.pl.remove_songs([self.SONG], False)
        self.failUnlessEqual(len(self.pl), 7 - 2 - 2)

    def test_remove_duplicated_song_leave_dupes(self):
        self.pl.remove_songs([self.SONGS[1]], True)
        self.failUnlessEqual(len(self.pl), len(self.SONGS) - 1)

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
        "~filename": dummy_path(u"/dev/urandom")})

    def setUp(self):
        self.success = False
        # Testing locally is VERY dangerous without this...
        self.assertTrue(_TEMP_DIR in PLAYLISTS or os.name == "nt",
                        msg="Failing, don't want to delete %s" % PLAYLISTS)
        try:
            shutil.rmtree(PLAYLISTS)
        except OSError:
            pass

        mkdir(PLAYLISTS)

        init_fake_app()

        self.lib = quodlibet.browsers.playlists.library = SongFileLibrary()
        self.lib.librarian = SongLibrarian()
        all_songs = SONGS + [self.ANOTHER_SONG]
        for af in all_songs:
            af.sanitize()
        self.lib.add(all_songs)

        self.big = pl = FileBackedPlaylist.new(PLAYLISTS, "Big", self.lib)
        pl.extend(SONGS)
        pl.write()

        self.small = pl = FileBackedPlaylist.new(PLAYLISTS, "Small", self.lib)
        pl.extend([self.ANOTHER_SONG])
        pl.write()

        PlaylistsBrowser.init(self.lib)

        self.bar = PlaylistsBrowser(self.lib)
        self.bar.connect('songs-selected', self._expected)
        self.bar._select_playlist(self.bar.playlists()[0])
        self.expected = None

    def tearDown(self):
        self.bar.destroy()
        self.lib.destroy()
        shutil.rmtree(PLAYLISTS)
        PlaylistsBrowser.deinit(self.lib)
        destroy_fake_app()

    def _expected(self, bar, songs, sort):
        songs.sort()
        if self.expected is not None:
            self.failUnlessEqual(self.expected, songs)
        self.success = True

    def _do(self):
        while Gtk.events_pending():
            Gtk.main_iteration()
        self.failUnless(self.success or self.expected is None)

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
        self.expected = list(sorted(SONGS))
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
        self.assertEquals(self.bar.playlists()[1], self.small)
        self.bar._rename(0, "zBig")
        self.assertEquals(self.bar.playlists()[0], self.small)
        self.assertEquals(self.bar.playlists()[1].name, "zBig")

    def test_default_display_pattern(self):
        pattern_text = self.bar.display_pattern_text
        self.failUnlessEqual(pattern_text, DEFAULT_PATTERN_TEXT)
        self.failUnless("<~name>" in pattern_text)

    def test_drag_data_get(self):
        b = self.bar
        song = AudioFile()
        song["~filename"] = fsnative(u"foo")
        sel = MockSelData()
        qltk.selection_set_songs(sel, [song])
        b._drag_data_get(None, None, sel, DND_QL, None)

    def test_deletion(self):
        def a_delete_event():
            ev = Gdk.Event()
            ev.type = Gdk.EventType.KEY_PRESS
            ev.keyval, accel_mod = Gtk.accelerator_parse("Delete")
            ev.state = Gtk.accelerator_get_default_mod_mask() & accel_mod
            return ev

        b = self.bar
        self._fake_browser_pack(b)
        event = a_delete_event()
        # This is selected in setUp()
        first_pl = b.playlists()[0]
        app.window.songlist.set_songs(first_pl)
        app.window.songlist.select_by_func(lambda x: True,
                                           scroll=False, one=True)
        original_length = len(first_pl)
        ret = b.key_pressed(event)
        self.failUnless(ret, msg="Didn't simulate a delete keypress")
        self.failUnlessEqual(len(first_pl), original_length - 1)

    def test_import(self):
        pl_name = u"_€3 œufs à Noël"
        pl = FileBackedPlaylist(_TEMP_DIR, pl_name, None)
        pl.extend(SONGS)
        pl.write()
        new_fn = os.path.splitext(text2fsn(pl.name))[0] + '.m3u'
        new_path = os.path.join(pl.dir, new_fn)
        os.rename(pl.path, new_path)
        added = self.bar._import_playlists([new_path], self.lib)
        self.failUnlessEqual(added, 1, msg="Failed to add '%s'" % new_path)
        os.unlink(new_path)
        pls = self.bar.playlists()
        self.failUnlessEqual(len(pls), 3)
        # Leading underscore makes it always the last entry
        imported = pls[-1]
        self.failUnlessEqual(imported.name, pl_name)

        def fns(songs):
            return [song('~filename') for song in songs]
        self.failUnlessEqual(fns(imported.songs), fns(pl.songs))

    @staticmethod
    def _fake_browser_pack(b):
        app.window.get_child().pack_start(b, True, True, 0)


class TPlaylistUtils(TestCase):

    def test_naming(self):
        self.failUnlessEqual(_name_for('/foo/bar.m3u'), 'bar')
        self.failUnlessEqual(_name_for('/foo/Will.I.Am.m3u'), 'Will.I.Am')

    def test_naming_default(self):
        self.failUnlessEqual(_name_for(''), __('New Playlist'))
