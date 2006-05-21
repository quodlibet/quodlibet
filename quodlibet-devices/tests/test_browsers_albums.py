from tests import TestCase, add

import browsers.albums
import widgets

from browsers.albums import AlbumList
from library import Library
from player import PlaylistPlayer
from qltk.watcher import SongWatcher

class TAlbumList(TestCase):
    Bar = AlbumList

    def setUp(self):
        widgets.library = browsers.albums.library = Library()
        widgets.watcher = SongWatcher()
        self.bar = self.Bar(widgets.watcher, PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))
        self.failUnless(self.bar.can_filter("album"))

    def tearDown(self):
        self.bar.destroy()
        widgets.library = browsers.search.library = Library()
        widgets.watcher.destroy()
        del(widgets.watcher)
add(TAlbumList)
