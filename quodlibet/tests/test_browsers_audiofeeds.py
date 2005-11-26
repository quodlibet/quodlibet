import gobject, gtk
from tests import TestCase, add

import widgets
from player import PlaylistPlayer
from browsers.audiofeeds import AudioFeeds
from qltk.watcher import SongWatcher

class TAudioFeeds(TestCase):
    def setUp(self):
        self.bar = AudioFeeds(SongWatcher(), PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
add(TAudioFeeds)
