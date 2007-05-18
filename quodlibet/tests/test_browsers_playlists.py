from tests import TestCase, add

import os
import tempfile

from quodlibet.browsers.playlists import ParseM3U, ParsePLS, Playlist, Playlists
from quodlibet.player import PlaylistPlayer
from quodlibet.library import SongLibrary

def makename():
    return tempfile.mkstemp()[1]

class TParsePlaylist(TestCase):
    def test_parse_empty(self):
        name = makename()
        file(name, "w").close()
        pl = self.Parse(name)
        os.unlink(name)
        self.failUnlessEqual(pl, [])
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
        p1 = Playlist.new("Does not exist")
        self.failUnlessEqual(p1, [])
        self.failUnlessEqual(p1.name, "Does not exist")
        p1.delete()

    def test_rename_working(self):
        p1 = Playlist.new("Foobar")
        p1.rename("Foo Quuxly")
        self.failUnlessEqual(p1.name, "Foo Quuxly")
        p1.delete()

    def test_rename_nothing(self):
        p1 = Playlist.new("Foobar")
        self.failUnlessRaises(ValueError, p1.rename, "")
        p1.delete()
    
    def test_rename_dup(self):
        p1 = Playlist.new("Foobar")
        p2 = Playlist.new("Crazy")
        self.failUnlessRaises(ValueError, p2.rename, "Foobar")
        p1.delete()
        p2.delete()
    
    def test_make_dup(self):
        p1 = Playlist.new("Does not exist")
        p2 = Playlist.new("Does not exist")
        self.failUnlessEqual(p1.name, "Does not exist")
        self.failUnless(p2.name.startswith("Does not exist"))
        self.failIfEqual(p1.name, p2.name)
        p1.delete()
        p2.delete()
add(TPlaylist)

class TPlaylists(TestCase):
    def setUp(self):
        self.library = SongLibrary()
        self.bar = Playlists(SongLibrary(), PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
        self.library.destroy()
add(TPlaylists)
