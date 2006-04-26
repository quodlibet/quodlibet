from tests import TestCase, add

import gtk

from qltk.queue import QueueExpander
from qltk.watcher import SongWatcher

class TQueueExpander(TestCase):
    def setUp(self):
        self.queue = QueueExpander(gtk.CheckMenuItem(), SongWatcher())

    def test_ctr(self):
        pass

    def tearDown(self):
        self.queue.destroy()
add(TQueueExpander)
