from tests import TestCase, add

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.mmkeys import MmKeys

class TMmKeys(TestCase):
    def setUp(self): self.keys = MmKeys(NullPlayer())
    def test_ctr(self): pass
    def test_block(self): self.keys.block()
    def test_unblock(self): self.keys.unblock()
add(TMmKeys)
