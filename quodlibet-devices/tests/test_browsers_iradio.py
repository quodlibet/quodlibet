from tests import TestCase, add

from browsers.iradio import InternetRadio
from player import PlaylistPlayer
from qltk.watcher import SongWatcher

class TInternetRadio(TestCase):
    def setUp(self):
        self.bar = InternetRadio(SongWatcher(), PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
add(TInternetRadio)
