from tests import TestCase, add

from qltk.exfalso import ExFalsoWindow
from library import SongLibrary

class TExFalsoWindow(TestCase):
    def setUp(self):
        self.ef = ExFalsoWindow(SongLibrary())

    def test_nothing(self):
        self.failUnless(self.ef.child)

    def tearDown(self):
        self.ef.destroy()
add(TExFalsoWindow)
