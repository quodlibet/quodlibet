# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.info import SongInfo
from quodlibet.library import SongLibrary


class TSongInfo(TestCase):
    def setUp(self):
        self.info = SongInfo(SongLibrary(), NullPlayer(), "")

    def test_ctr(self):
        pass

    def tearDown(self):
        self.info.destroy()
