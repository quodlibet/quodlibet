from tests import TestCase, add

import quodlibet.browsers.albums
import quodlibet.widgets

from quodlibet.browsers.albums import AlbumList
from quodlibet.library import SongLibrary
from quodlibet.player import PlaylistPlayer

class TAlbumList(TestCase):
    Bar = AlbumList

    def setUp(self):
        self.bar = self.Bar(SongLibrary(), PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))
        self.failUnless(self.bar.can_filter("album"))

    def tearDown(self):
        self.bar.destroy()
add(TAlbumList)
