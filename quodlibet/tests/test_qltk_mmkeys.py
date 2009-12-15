from tests import TestCase, add

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.mmkeys_ import MmKeys

class TMmKeys(TestCase):
    def setUp(self): self.keys = MmKeys(NullPlayer())
    def test_ctr(self): pass
add(TMmKeys)
