from tests import TestCase, add

from quodlibet.library import SongLibrary
from quodlibet.browsers.iradio import InternetRadio
from quodlibet.player import PlaylistPlayer

class TInternetRadio(TestCase):
    def setUp(self):
        self.bar = InternetRadio(SongLibrary(), PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
add(TInternetRadio)
