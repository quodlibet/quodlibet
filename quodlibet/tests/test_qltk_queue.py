from tests import TestCase, add

import gtk

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.queue import QueueExpander
from quodlibet.library import SongLibrary
import quodlibet.config

class TQueueExpander(TestCase):
    def setUp(self):
        quodlibet.config.init()
        player = NullPlayer()
        self.queue = QueueExpander(gtk.CheckMenuItem(), SongLibrary(), player)

    def test_ctr(self):
        pass

    def tearDown(self):
        self.queue.destroy()
        quodlibet.config.quit()
add(TQueueExpander)
