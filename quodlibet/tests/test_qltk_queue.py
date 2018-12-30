# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from quodlibet.order.reorder import OrderShuffle
from tests import TestCase

from quodlibet.player.nullbe import NullPlayer
from quodlibet.formats import DUMMY_SONG
from quodlibet.qltk.queue import QueueExpander, PlaybackStatusIcon, \
    PlayQueue, QUEUE
from quodlibet.library import SongLibrary
import quodlibet.config


class TPlayQueue(TestCase):

    def test_save_restore(self):
        player = NullPlayer()
        lib = SongLibrary()
        lib.librarian = None
        lib.add([DUMMY_SONG])

        try:
            os.unlink(QUEUE)
        except OSError:
            pass

        q = PlayQueue(lib, player)
        q.get_model().append(row=[DUMMY_SONG])
        q.destroy()

        q = PlayQueue(lib, player)
        model = q.get_model()
        assert model.values()[0] is DUMMY_SONG


class TQueueExpander(TestCase):

    def setUp(self):
        quodlibet.config.init()
        player = NullPlayer()
        self.queue = QueueExpander(SongLibrary(), player)

    def test_ctr(self):
        pass

    def test_status_icon(self):
        widget = PlaybackStatusIcon()
        widget.play()
        widget.stop()
        widget.pause()
        widget.pause()

    def test_random_at_startup(self):
        self.failIf(isinstance(self.queue.model.order, OrderShuffle))
        quodlibet.config.set("memory", "shufflequeue", True)
        self.queue = self.queue = QueueExpander(SongLibrary(), NullPlayer())
        # See issue #2411
        self.failUnless(isinstance(self.queue.model.order, OrderShuffle))

    def tearDown(self):
        self.queue.destroy()
        quodlibet.config.quit()
