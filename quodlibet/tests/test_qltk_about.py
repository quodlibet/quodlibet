from tests import TestCase, add

from quodlibet.qltk.about import AboutQuodLibet
from quodlibet.player.nullbe import NullPlayer

class TAboutQuodLibet(TestCase):
    def test_ctr(self):
        AboutQuodLibet(None, NullPlayer()).destroy()
add(TAboutQuodLibet)
