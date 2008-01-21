from tests import TestCase, add

from quodlibet.browsers.filesystem import FileSystem
from quodlibet.player import PlaylistPlayer
from quodlibet.library import SongLibrary

class TFileSystem(TestCase):
    def setUp(self):
        self.bar = FileSystem(SongLibrary(), PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))
        self.failUnless(self.bar.can_filter("~dirname"))

    def tearDown(self):
        self.bar.destroy()
add(TFileSystem)
