from tests import TestCase, add

import gtk

import widgets

from player import PlaylistPlayer
from qltk.quodlibet import MainSongList, QuodLibetWindow
from qltk.watcher import SongWatcher

class TMainSongList(TestCase):
    def setUp(self):
        self.watcher = SongWatcher()
        self.player = PlaylistPlayer('fakesink')
        self.list = MainSongList(self.watcher, self.player, gtk.CheckButton())

    def test_ctr(self):
        pass

    def tearDown(self):
        self.list.destroy()
        self.watcher.destroy()
        self.player.quit()
add(TMainSongList)

class TQuodLibetWindow(TestCase):
    def setUp(self):
        widgets.watcher = self.watcher = SongWatcher()
        self.player = PlaylistPlayer('fakesink')
        widgets.main = self.win = QuodLibetWindow(self.watcher, self.player)
        self.player.setup(self.watcher, self.win.playlist, None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        self.watcher.destroy()
        self.player.quit()
        del(widgets.main)
        del(widgets.watcher)
add(TQuodLibetWindow)
