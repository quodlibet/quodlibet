from tests import TestCase, add

import gtk

from player import PlaylistPlayer
from qltk.queue import QueueExpander
from library import SongLibrary

class TQueueExpander(TestCase):
    def setUp(self):
        player = PlaylistPlayer('fakesink')
        self.queue = QueueExpander(gtk.CheckMenuItem(), SongLibrary(), player)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.queue.destroy()
add(TQueueExpander)
