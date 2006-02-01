import gobject, gtk
from tests import TestCase, add

import widgets
from player import PlaylistPlayer
from browsers.filesystem import FileSystem
from qltk.watcher import SongWatcher

class TFileSystem(TestCase):
    def setUp(self):
        self.bar = FileSystem(SongWatcher(), PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))
        self.failUnless(self.bar.can_filter("~dirname"))

    def tearDown(self):
        self.bar.destroy()
add(TFileSystem)
