from tests import TestCase, add

from quodlibet.qltk.about import AboutQuodLibet

class TAboutQuodLibet(TestCase):
    def test_ctr(self):
        from quodlibet.player import PlaylistPlayer
        AboutQuodLibet(None, PlaylistPlayer("fakesink")).destroy()
add(TAboutQuodLibet)
