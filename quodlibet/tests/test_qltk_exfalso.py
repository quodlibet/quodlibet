from tests import TestCase, add
from qltk.exfalso import ExFalsoWindow
from qltk.watcher import SongWatcher
from tempfile import mkdtemp

class TExFalsoWindow(TestCase):
    def setUp(self):
        self.ef = ExFalsoWindow(SongWatcher())

    def test_nothing(self):
        self.failUnless(self.ef.child)

    def tearDown(self):
        self.ef.destroy()
add(TExFalsoWindow)
