from tests import TestCase, add

from quodlibet.library import SongLibrary
from quodlibet.browsers.iradio import InternetRadio
from quodlibet.player.nullbe import NullPlayer
import quodlibet.config

class TInternetRadio(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.bar = InternetRadio(SongLibrary(), NullPlayer())

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
        quodlibet.config.quit()
add(TInternetRadio)
