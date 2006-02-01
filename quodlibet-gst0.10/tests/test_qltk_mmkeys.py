from tests import add, TestCase
from qltk.mmkeys import MmKeys
from player import PlaylistPlayer

class TMmKeys(TestCase):
    def setUp(self): self.keys = MmKeys(PlaylistPlayer('fakesink'))
    def test_ctr(self): pass
    def test_block(self): self.keys.block()
    def test_unblock(self): self.keys.unblock()
add(TMmKeys)
