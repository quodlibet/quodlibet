from tests import TestCase, add

import gtk

from quodlibet import widgets

from quodlibet.player import PlaylistPlayer
from quodlibet.qltk.quodlibetwindow import MainSongList, QuodLibetWindow
from quodlibet.library import SongLibrary

class TMainSongList(TestCase):
    def setUp(self):
        self.library = SongLibrary()
        self.player = PlaylistPlayer('fakesink')
        self.list = MainSongList(self.library, self.player, gtk.CheckButton())

    def test_ctr(self):
        pass

    def tearDown(self):
        self.list.destroy()
        self.library.destroy()
        self.player.destroy()
add(TMainSongList)

class TQuodLibetWindow(TestCase):
    def setUp(self):
        self.player = PlaylistPlayer('fakesink')
        self.library = SongLibrary()
        widgets.main = self.win = QuodLibetWindow(self.library, self.player)
        self.player.setup(self.win.playlist, None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        self.library.destroy()
        self.player.destroy()
        del(widgets.main)
add(TQuodLibetWindow)
