from tests import add, TestCase

class TMainSongList(TestCase):
    def setUp(self):
        from qltk.watcher import SongWatcher
        from player import PlaylistPlayer
        self.watcher = SongWatcher()
        self.player = PlaylistPlayer('fakesink')
        from qltk.quodlibet import MainSongList
        self.list = MainSongList(self.watcher, self.player)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.list.destroy()
        self.watcher.destroy()
        self.player.quit()
add(TMainSongList)

class TQuodLibetWindow(TestCase):
    def setUp(self):
        import player
        player.init("fakesink")
        from qltk.watcher import SongWatcher
        import widgets
        widgets.watcher = self.watcher = SongWatcher()
        from qltk.quodlibet import QuodLibetWindow
        widgets.main = self.win = QuodLibetWindow(self.watcher)
        player.playlist.setup(self.watcher, self.win.playlist, None)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.win.destroy()
        self.watcher.destroy()
        import player
        player.playlist.quit()
        player.playlist = None
        import widgets
        del(widgets.main)
        del(widgets.watcher)
add(TQuodLibetWindow)
