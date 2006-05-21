from tests import add, TestCase

import gtk
from qltk.watcher import SongWatcher
from player import PlaylistPlayer

class TSongWatcher(TestCase):
    def setUp(self):
        self.watcher = SongWatcher()

    def __changed(self, watcher, song, expected):
        self.failUnlessEqual(expected.pop(0), song)

    def __test_signal(self, sig):
        expected = [[0], [1], [2], [3], [4], [5]]
        self.watcher.connect(sig, self.__changed, expected)
        map(getattr(self.watcher, sig), list(expected))
        while gtk.events_pending(): gtk.main_iteration()
        self.failIf(expected)

    def test_changed(self): self.__test_signal('changed')
    def test_removed(self): self.__test_signal('removed')

    def tearDown(self):
        self.watcher.destroy()

add(TSongWatcher)

