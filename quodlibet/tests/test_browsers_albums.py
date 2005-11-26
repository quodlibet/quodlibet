import gobject, gtk
from tests import TestCase, add

import widgets
import browsers.albums
from player import PlaylistPlayer
from browsers.albums import AlbumList
from qltk.watcher import SongWatcher

from library import Library

class TAlbumList(TestCase):
    Bar = AlbumList
    def setUp(self):
        widgets.library = browsers.albums.library = Library()
        from widgets import widgets as ws
        ws.watcher = SongWatcher()
        self.bar = self.Bar(ws.watcher, PlaylistPlayer('fakesink'))

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))
        self.failUnless(self.bar.can_filter("album"))

    def tearDown(self):
        self.bar.destroy()
        widgets.library = browsers.search.library = None
        from widgets import widgets as ws
        ws.watcher.destroy()
        del(ws.watcher)
add(TAlbumList)
