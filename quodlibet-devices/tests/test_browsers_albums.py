from tests import TestCase, add

import browsers.albums
import widgets

from browsers.albums import AlbumList
from library import SongLibrary
from player import PlaylistPlayer

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
