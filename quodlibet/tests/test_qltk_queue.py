# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.queue import QueueExpander, PlaybackStatusIcon
from quodlibet.library import SongLibrary
import quodlibet.config


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

    def tearDown(self):
        self.queue.destroy()
        quodlibet.config.quit()
