# -*- coding: utf-8 -*-
from quodlibet.browsers.playlists.prefs import DEFAULT_PATTERN_TEXT
from quodlibet.browsers.playlists.util import *
from quodlibet.util.collection import FileBackedPlaylist
from tests import TestCase, DATA_DIR, mkstemp, mkdtemp, _TEMP_DIR
from .helper import dummy_path

import os
import shutil

from quodlibet.browsers.playlists import PlaylistsBrowser
from quodlibet.library import SongLibrary
import quodlibet.config
from quodlibet.formats import AudioFile
from quodlibet.util.path import fsnative2glib, mkdir
from quodlibet.library.librarians import SongLibrarian
from quodlibet.library.libraries import FileLibrary
from tests.test_browsers_search import SONGS, TSearchBar


class TParsePlaylist(TestCase):
    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()


class TParsePlaylistMixin(object):

    def test_parse_empty(self):
        h, name = mkstemp()
        os.close(h)
        open(name, "w").close()
        pl = self.Parse(name)
        os.unlink(name)
        self.failUnlessEqual(0, len(pl))
        pl.delete()

    def test_parse_onesong(self):
        h, name = mkstemp()
        os.close(h)
        with open(name, "wb") as f:
            target = self.prefix
            target += fsnative2glib(os.path.join(DATA_DIR, "silence-44-s.ogg"))
            f.write(target)
        list = self.Parse(name)
        os.unlink(name)
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(list[0]("title"), "Silence")
        list.delete()

    def test_parse_onesong_uri(self):
        h, name = mkstemp()
        os.close(h)
        target = os.path.join(DATA_DIR, "silence-44-s.ogg")
        from quodlibet.util.uri import URI
        target = URI.frompath(target)
        target = self.prefix + target
        with open(name, "w") as f:
            f.write(target)
        list = self.Parse(name)
        os.unlink(name)
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(list[0]("title"), "Silence")
        list.delete()


class TParseM3U(TParsePlaylist, TParsePlaylistMixin):
    Parse = staticmethod(parse_m3u)
    prefix = ""


class TParsePLS(TParsePlaylist, TParsePlaylistMixin):
    Parse = staticmethod(parse_pls)
    prefix = "File1="


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
        self.lib = quodlibet.browsers.search.library = FileLibrary()
        quodlibet.browsers.search.library.librarian = SongLibrarian()
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


class TPlaylistsBrowser(TSearchBar):
    Bar = PlaylistsBrowser

    ANOTHER_SONG = AudioFile({
        "title": "lonely",
        "artist": "new artist",
        "~filename": dummy_path(u"/dev/urandom")})

    def setUp(self):
        # Testing locally is VERY dangerous without this...
        self.assertTrue(_TEMP_DIR in PLAYLISTS or os.name == "nt",
                        msg="Failing, don't want to delete %s" % PLAYLISTS)
        try:
            shutil.rmtree(PLAYLISTS)
        except OSError:
            pass

        mkdir(PLAYLISTS)

        self.lib = quodlibet.browsers.playlists.library = SongLibrary()
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
