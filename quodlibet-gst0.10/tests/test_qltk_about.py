from tests import add, TestCase
from qltk.about import AboutWindow

class TAboutWindow(TestCase):
    def test_ctr(self):
        from player import PlaylistPlayer
        AboutWindow(None, PlaylistPlayer("fakesink"), run=False).destroy()
add(TAboutWindow)
