from tests import TestCase, add

from quodlibet.browsers.audiofeeds import AudioFeeds
from quodlibet.player.nullbe import NullPlayer
from quodlibet.library import SongLibrary
import quodlibet.config

class TAudioFeeds(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.library = SongLibrary()
        self.bar = AudioFeeds(self.library, NullPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))

    def tearDown(self):
        self.bar.destroy()
        self.library.destroy()
        quodlibet.config.quit()
add(TAudioFeeds)
