from tests import add, TestCase
from qltk.about import AboutQuodLibet

class TAboutQuodLibet(TestCase):
    def test_ctr(self):
        from player import PlaylistPlayer
        AboutQuodLibet(None, PlaylistPlayer("fakesink")).destroy()
add(TAboutQuodLibet)
