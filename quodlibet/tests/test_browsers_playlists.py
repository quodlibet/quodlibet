from quodlibet.browsers.playlists.util import parse_m3u, parse_pls
from quodlibet.util.collection import Playlist
from tests import TestCase, add, DATA_DIR, mkstemp, mkdtemp

import os
import shutil

from quodlibet.browsers.playlists import PlaylistsBrowser
from quodlibet.player.nullbe import NullPlayer
from quodlibet.library import SongLibrary
import quodlibet.config
from quodlibet.formats._audio import AudioFile
from quodlibet.library.librarians import SongLibrarian
from quodlibet.library.libraries import FileLibrary


class TParsePlaylist(TestCase):
    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()

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
        f = file(name, "w")
        target = self.prefix
        target += os.path.join(DATA_DIR, "silence-44-s.ogg")
        f.write(target)
        f.close()
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


class TParseM3U(TParsePlaylist):
    Parse = staticmethod(parse_m3u)
    prefix = ""
add(TParseM3U)


class TParsePLS(TParsePlaylist):
    Parse = staticmethod(parse_pls)
    prefix = "File1="
add(TParsePLS)


class TPlaylistIntegration(TestCase):
    DUPLICATES = 1
    SONG = AudioFile({
                "title": "two",
                "artist": "mu",
                "~filename": "/dev/zero"})
    SONGS = [
        AudioFile({
                "title": "one",
                "artist": "piman",
                "~filename": "/dev/null"}),
        SONG,
        AudioFile({
                "title": "three",
                "artist": "boris",
                "~filename": "/bin/ls"}),
        AudioFile({
                "title": "four",
                "artist": "random",
                "album": "don't stop",
                "labelid": "65432-1",
                "~filename": "/dev/random"}),
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
        self.pl = Playlist.new(self._dir, "Foobar")
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
        self.pl.remove_songs([self.SONGS[0]], self.lib)
        self.failUnlessEqual(len(self.pl), len(self.SONGS) - 1)

    def test_remove_duplicated_song(self):
        self.failUnlessEqual(self.SONGS[1], self.SONGS[4])
        self.pl.remove_songs([self.SONGS[1]], self.lib)
        self.failUnlessEqual(len(self.pl), len(self.SONGS) - 2)

    def test_remove_multi_duplicated_song(self):
        self.pl.extend([self.SONG, self.SONG])
        self.failUnlessEqual(len(self.pl), 7)
        self.pl.remove_songs([self.SONG], self.lib, False)
        self.failUnlessEqual(len(self.pl), 7 - 2 - 2)

    def test_remove_duplicated_song_leave_dupes(self):
        self.pl.remove_songs([self.SONGS[1]], self.lib, True)
        self.failUnlessEqual(len(self.pl), len(self.SONGS) - 1)


add(TPlaylistIntegration)


class TPlaylists(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.library = SongLibrary()
        self.bar = PlaylistsBrowser(SongLibrary(), NullPlayer())

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
        self.library.destroy()
        quodlibet.config.quit()
add(TPlaylists)
