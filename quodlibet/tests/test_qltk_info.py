from tests import TestCase, add

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.info import SongInfo
from quodlibet.library import SongLibrary

class TSongInfo(TestCase):
    def setUp(self):
        self.info = SongInfo(SongLibrary(), NullPlayer())
    def test_ctr(self): pass
    def tearDown(self):
        self.info.destroy()
add(TSongInfo)
