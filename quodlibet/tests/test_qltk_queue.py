import gtk
from tests import add, TestCase
from qltk.watcher import SongWatcher
from qltk.queue import QueueExpander

class TQueueExpander(TestCase):
    def setUp(self):
        self.queue = QueueExpander(gtk.CheckMenuItem(), SongWatcher())

    def test_ctr(self):
        pass

    def tearDown(self):
        self.queue.destroy()
add(TQueueExpander)
