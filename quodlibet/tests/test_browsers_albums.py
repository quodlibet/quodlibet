from tests import TestCase, add

import quodlibet.browsers.albums
import quodlibet.widgets
import quodlibet.config

from quodlibet.browsers.albums import AlbumList
from quodlibet.library import SongLibrary
from quodlibet.player.nullbe import NullPlayer

class TAlbumList(TestCase):
    Bar = AlbumList

    def setUp(self):
        quodlibet.config.init()
        self.bar = self.Bar(SongLibrary(), NullPlayer())

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))
        self.failUnless(self.bar.can_filter("album"))

    def tearDown(self):
        self.bar.destroy()
        quodlibet.config.quit()
add(TAlbumList)
