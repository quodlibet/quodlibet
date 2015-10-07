# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.qltk.controls import PlayControls, VolumeMenu, SeekBar, \
    TimeLabel
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

    def test_seekbar(self):
        w = SeekBar(self.p, self.l)
        w.destroy()

    def test_volume(self):
        w = Volume(self.p)
        w.destroy()

    def test_time_label(self):
        l = TimeLabel()
        l.set_time(42)
        time_text = l.get_text()
        l.set_disabled(True)
        disabled_text = l.get_text()
        self.assertNotEqual(time_text, disabled_text)
        l.set_disabled(False)
        self.assertEqual(l.get_text(), time_text)
