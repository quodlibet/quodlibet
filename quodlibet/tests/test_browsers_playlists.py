from tests import TestCase, add

import os
import tempfile

from quodlibet.browsers.playlists import ParseM3U, ParsePLS, Playlist, Playlists
from quodlibet.player.nullbe import NullPlayer
from quodlibet.library import SongLibrary
import quodlibet.config
from quodlibet.formats._audio import AudioFile
from quodlibet.library.songs import SongLibrarian, FileLibrary

PLAYLISTS = tempfile.gettempdir()

def makename():
    return tempfile.mkstemp()[1]

class TParsePlaylist(TestCase):
    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()

    def test_parse_empty(self):
        name = makename()
        file(name, "w").close()
        pl = self.Parse(name)
        os.unlink(name)
        self.failUnlessEqual(0, len(pl))
        pl.delete()

    def test_parse_onesong(self):
        name = makename()
        f = file(name, "w")
        target = self.prefix
        target += os.path.join(os.getcwd(), "tests/data/silence-44-s.ogg")
        f.write(target)
        f.close()
        list = self.Parse(name)
        os.unlink(name)
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(list[0]("title"), "Silence")
        list.delete()

    def test_parse_onesong_uri(self):
        name = makename()
        target = os.path.join(os.getcwd(), "tests/data/silence-44-s.ogg")
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
    Parse = staticmethod(ParseM3U)
    prefix = ""
add(TParseM3U)

class TParsePLS(TParsePlaylist):
    Parse = staticmethod(ParsePLS)
    prefix = "File1="
add(TParsePLS)

class TPlaylist(TestCase):
    def test_make(self):
        p1 = Playlist.new(PLAYLISTS, "Does not exist")
        self.failUnlessEqual(0, len(p1))
        self.failUnlessEqual(p1.name, "Does not exist")
        p1.delete()

    def test_rename_working(self):
        p1 = Playlist.new(PLAYLISTS, "Foobar")
        p1.rename("Foo Quuxly")
        self.failUnlessEqual(p1.name, "Foo Quuxly")
        p1.delete()

    def test_rename_nothing(self):
        p1 = Playlist.new(PLAYLISTS, "Foobar")
        self.failUnlessRaises(ValueError, p1.rename, "")
        p1.delete()

    def test_rename_dup(self):
        p1 = Playlist.new(PLAYLISTS, "Foobar")
        p2 = Playlist.new(PLAYLISTS, "Crazy")
        self.failUnlessRaises(ValueError, p2.rename, "Foobar")
        p1.delete()
        p2.delete()

    def test_make_dup(self):
        p1 = Playlist.new(PLAYLISTS, "Does not exist")
        p2 = Playlist.new(PLAYLISTS, "Does not exist")
        self.failUnlessEqual(p1.name, "Does not exist")
        self.failUnless(p2.name.startswith("Does not exist"))
        self.failIfEqual(p1.name, p2.name)
        p1.delete()
        p2.delete()

add(TPlaylist)


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
        self.pl = Playlist.new(PLAYLISTS, "Foobar")
        self.pl.extend(self.SONGS)

    def tearDown(self):
        self.pl.delete()
        self.lib.destroy()
        self.lib.librarian.destroy()
        quodlibet.config.quit()

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
        self.failUnlessEqual(len(self.pl), 7-2-2)

    def test_remove_duplicated_song_leave_dupes(self):
        self.pl.remove_songs([self.SONGS[1]], self.lib, True)
        self.failUnlessEqual(len(self.pl), len(self.SONGS) - 1)


add(TPlaylistIntegration)


class TPlaylists(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.library = SongLibrary()
        self.bar = Playlists(SongLibrary(), NullPlayer())

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
        self.library.destroy()
        quodlibet.config.quit()
add(TPlaylists)
