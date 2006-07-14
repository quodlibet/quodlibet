from tests import TestCase, add

from player import PlaylistPlayer
from qltk.info import SongInfo
from library import SongLibrary

class TSongInfo(TestCase):
    def setUp(self):
        self.info = SongInfo(SongLibrary(), PlaylistPlayer('fakesink'))
    def test_ctr(self): pass
    def tearDown(self):
        self.info.destroy()
add(TSongInfo)
