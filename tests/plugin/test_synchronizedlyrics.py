# Copyright 2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import config
from tests.plugin import PluginTestCase


class TSynchronizedlyrics(PluginTestCase):
    def setUp(self):
        self.mod = self.modules["SynchronizedLyrics"]
        self.plugin = self.mod.SynchronizedLyrics()

    def tearDown(self):
        config.quit()

    def test_empty_parsing(self):
        assert self.plugin._parse_lrc("") == []

    def test_lrc_parsing(self):
        lrc = """
        [ti:Test Thing]
        [length:66:66.66]
        [01:23.45] This is some text
        [01:01.00]Starting here?
        [61:00.00]Past the hour mark now!
        """
        assert self.plugin._parse_lrc(lrc) == [
            (1000 * 61, "Starting here?"),
            (1000 * (60 + 23.45), "This is some text"),
            (1000 * 61.0 * 60, "Past the hour mark now!")
        ]
