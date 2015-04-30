# -*- coding: utf-8 -*-
from quodlibet.browsers.playlists.util import parse_m3u, parse_pls, PLAYLISTS
from quodlibet.util.collection import Playlist
from tests import TestCase, DATA_DIR, mkstemp, mkdtemp

import os
import shutil

from quodlibet.browsers.playlists import PlaylistsBrowser
from quodlibet.library import SongLibrary
import quodlibet.config
from quodlibet.formats._audio import AudioFile
from quodlibet.util.path import fsnative, fsnative2glib
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
        file(name, "w").close()
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
        f = file(name, "w")
        f.write(target)
        f.close()
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
                "~filename": fsnative(u"/dev/zero")})
    SONGS = [
        AudioFile({
                "title": "one",
                "artist": "piman",
                "~filename": fsnative(u"/dev/null")}),
        SONG,
        AudioFile({
                "title": "three",
                "artist": "boris",
                "~filename": fsnative(u"/bin/ls")}),
        AudioFile({
                "title": "four",
                "artist": "random",
                "album": "don't stop",
                "labelid": "65432-1",
                "~filename": fsnative(u"/dev/random")}),
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
        self.pl = Playlist.new(self._dir, "Foobar", self.lib)
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
        pl = Playlist.new(self._dir, "Foobar")
        pl.extend(self.SONGS)
        self.assertTrue(len(pl))
        pl.remove_songs(self.SONGS, False)
        self.assertFalse(len(pl))


class TPlaylists(TSearchBar):
    Bar = PlaylistsBrowser
    ANOTHER_SONG = AudioFile({
        "title": "lonely",
        "artist": "new artist",
        "~filename": fsnative(u"/dev/urandom")})

    @classmethod
    def setUpClass(cls):
        # Only want to do this playlists setup once per test class...
        quodlibet.config.init()
        cls.lib = quodlibet.browsers.playlists.library = SongLibrary()
        cls.lib.librarian = SongLibrarian()
        all_songs = SONGS + [cls.ANOTHER_SONG]
        for af in all_songs:
            af.sanitize()
        cls.lib.add(all_songs)
        cls._create_temp_playlist_with("Big", SONGS)
        cls._create_temp_playlist_with("Small", [cls.ANOTHER_SONG])
        PlaylistsBrowser.init(cls.lib)

    @classmethod
    def _create_temp_playlist_with(cls, name, songs):
        pl = Playlist.new(PLAYLISTS, name, cls.lib)
        pl.extend(songs)
        pl.write()

    def setUp(self):
        self.bar = PlaylistsBrowser(self.lib)
        self.bar.connect('songs-selected', self._expected)
        self.bar._select_playlist(self.bar.playlists()[0])
        self.expected = None

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

    def tearDown(self):
        self.bar.destroy()
        self.lib.destroy()

    @classmethod
    def tearDownClass(cls):
        quodlibet.config.quit()
