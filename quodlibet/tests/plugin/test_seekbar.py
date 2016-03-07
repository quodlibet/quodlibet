# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from tests.plugin import PluginTestCase

from quodlibet.player.nullbe import NullPlayer
from quodlibet.library import SongLibrary


class TSeekBar(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["SeekBar"]

    def tearDown(self):
        del self.mod

    def test_create(self):
        SeekBar = self.mod.SeekBar
        SeekBar(NullPlayer(), SongLibrary()).destroy()
