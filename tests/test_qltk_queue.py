# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from time import sleep
from typing import List

from quodlibet.order.reorder import OrderShuffle
from senf import bytes2fsn
from tests import TestCase, run_gtk_loop

from quodlibet.player.nullbe import NullPlayer
from quodlibet.formats import DUMMY_SONG
from quodlibet.qltk.queue import QueueExpander, PlaybackStatusIcon, \
    PlayQueue, QUEUE
from quodlibet.library import SongLibrary
import quodlibet.config


class TPlayQueue(TestCase):
    def setUp(self):
        self.player = NullPlayer()
        self.lib = SongLibrary()
        self.lib.librarian = None
        self.lib.add([DUMMY_SONG])
        try:
            os.unlink(QUEUE)
        except OSError:
            pass

    def test_save_restore(self):
        q = PlayQueue(self.lib, self.player)
        q.get_model().append(row=[DUMMY_SONG])
        q.destroy()

        q = PlayQueue(self.lib, self.player)
        model = q.get_model()
        assert model.values()[0] is DUMMY_SONG

    def test_autosave(self):
        q = PlayQueue(self.lib, self.player, autosave_interval_secs=1)
        assert q._tid
        q.get_model().append(row=[DUMMY_SONG])
        sleep(1.1)
        run_gtk_loop()
        assert self.get_queue() == [DUMMY_SONG("~filename")]
        q.destroy()
        # Doesn't prove much but still
        assert not q._tid

    def get_queue(self) -> List[str]:
        try:
            with open(QUEUE, "rb") as f:
                return [bytes2fsn(line.strip(), "utf-8") for line in f.readlines()]
        except FileNotFoundError:
            return []

    def test_autosave_batched(self):
        q = PlayQueue(self.lib, self.player, autosave_interval_secs=None)
        model = q.get_model()
        model.append(row=[DUMMY_SONG])
        run_gtk_loop()
        assert not self.get_queue()
        for _i in range(PlayQueue._MAX_PENDING + 1):
            model.append(row=[DUMMY_SONG])
        run_gtk_loop()
        assert len(self.get_queue()) == PlayQueue._MAX_PENDING + 1


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
