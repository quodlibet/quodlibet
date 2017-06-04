# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests.plugin import PluginTestCase
from tests.helper import visible

from quodlibet.player.nullbe import NullPlayer
from quodlibet.formats import AudioFile


class TWaveformSeekBar(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["WaveformSeekBar"]

    def tearDown(self):
        del self.mod

    def test_main(self):
        WaveformScale = self.mod.WaveformScale

        player = NullPlayer()
        player.info = AudioFile({"~#length": 10})
        scale = WaveformScale(player)
        scale.compute_redraw_interval()
        scale.compute_redraw_area()

        with visible(scale):
            scale.compute_redraw_interval()
            scale.compute_redraw_area()
