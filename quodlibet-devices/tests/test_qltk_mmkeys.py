from tests import TestCase, add

from player import PlaylistPlayer
from qltk.mmkeys import MmKeys

class TMmKeys(TestCase):
    def setUp(self): self.keys = MmKeys(PlaylistPlayer('fakesink'))
    def test_ctr(self): pass
    def test_block(self): self.keys.block()
    def test_unblock(self): self.keys.unblock()
add(TMmKeys)
