from tests import TestCase, add

from quodlibet.player import PlaylistPlayer
from quodlibet.qltk.info import SongInfo
from quodlibet.library import SongLibrary

class TSongInfo(TestCase):
    def setUp(self):
        self.info = SongInfo(SongLibrary(), PlaylistPlayer('fakesink'))
    def test_ctr(self): pass
    def tearDown(self):
        self.info.destroy()
add(TSongInfo)
