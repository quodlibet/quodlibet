from tests import add, TestCase
from qltk.info import SongInfo
from qltk.watcher import SongWatcher
from player import PlaylistPlayer

class TSongInfo(TestCase):
    def setUp(self):
        self.info = SongInfo(SongWatcher(), PlaylistPlayer('fakesink'))
    def test_ctr(self): pass
    def tearDown(self):
        self.info.destroy()
add(TSongInfo)
