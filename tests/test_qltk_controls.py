# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.qltk.controls import PlayControls, VolumeMenu
from quodlibet.qltk.controls import Volume
from quodlibet.library import SongLibrary
from quodlibet.player.nullbe import NullPlayer
from quodlibet import config


class TControls(TestCase):
    def setUp(self):
        config.init()
        self.p = NullPlayer()
        self.l = SongLibrary()

    def tearDown(self):
        config.quit()

    def test_controls(self):
        w = PlayControls(self.p, self.l)
        w.destroy()

    def test_volumemenu(self):
        w = VolumeMenu(self.p)
        w.destroy()

    def test_volume(self):
        w = Volume(self.p)
        w.destroy()
