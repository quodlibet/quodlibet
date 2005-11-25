import os
from tests import add, TestCase
from qltk.watcher import SongWatcher
from browsers.playlists import ParseM3U, ParsePLS, Playlist, Playlists

import tempfile
def makename(): return tempfile.mkstemp()[1]

class TParsePlaylist(TestCase):
    def test_parse_empty(self):
        name = makename()
        file(name, "w").close()
        pl = self.Parse(name)
        self.failUnlessEqual(pl, [])
        os.unlink(name)
        pl.delete()

    def test_parse_garbage(self):
        name = makename()
        f = file(name, "w")
        f.write("this file\nis on\ncrack")
        f.close()

    def test_parse_onesong(self):
        name = makename()
        f = file(name, "w")
        target = self.prefix
        target += os.path.join(os.getcwd(), "tests/data/silence-44-s.ogg")
        f.write(os.path.join(os.getcwd(), "tests/data/silence-44-s.ogg"))
        f.close()
        list = self.Parse(name)
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(list[0]("title"), "Silence")
        os.unlink(name)
        list.delete()

    def test_parse_onesong_uri(self):
        name = makename()
        target = self.prefix
        target += os.path.join(os.getcwd(), "tests/data/silence-44-s.ogg")
        import urllib
        target = "file://" + urllib.pathname2url(target)
        f = file(name, "w")
        f.write(target)
        f.close()
        list = self.Parse(name)
        self.failUnlessEqual(len(list), 1)
        self.failUnlessEqual(list[0]("title"), "Silence")
        os.unlink(name)
        list.delete()

class TParseM3U(TParsePlaylist):
    Parse = staticmethod(ParseM3U)
    prefix = ""
add(TParseM3U)

class TParsePLS(TParsePlaylist):
    Parse = staticmethod(ParseM3U)
    prefix = "File1="
add(TParseM3U)

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
    def test_ctr(self):
        Playlists(SongWatcher(), False).destroy()
        Playlists(SongWatcher(), True).destroy()
add(TPlaylists)
