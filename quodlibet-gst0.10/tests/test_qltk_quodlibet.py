from tests import add, TestCase
from qltk.watcher import SongWatcher
from player import PlaylistPlayer
import gtk

class TMainSongList(TestCase):
    def setUp(self):
        self.watcher = SongWatcher()
        self.player = PlaylistPlayer('fakesink')
        from qltk.quodlibet import MainSongList
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
        from qltk.watcher import SongWatcher
        import widgets
        widgets.watcher = self.watcher = SongWatcher()
        from qltk.quodlibet import QuodLibetWindow
        self.player = PlaylistPlayer('fakesink')
        widgets.main = self.win = QuodLibetWindow(self.watcher, self.player)
        self.player.setup(self.watcher, self.win.playlist, None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        self.watcher.destroy()
        self.player.quit()
        import widgets
        del(widgets.main)
        del(widgets.watcher)
add(TQuodLibetWindow)
