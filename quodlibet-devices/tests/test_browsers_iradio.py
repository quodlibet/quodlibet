from tests import TestCase, add

from library import SongLibrary
from browsers.iradio import InternetRadio
from player import PlaylistPlayer

class TInternetRadio(TestCase):
    def setUp(self):
        self.bar = InternetRadio(SongLibrary(), PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
add(TInternetRadio)
