# -*- coding: utf-8 -*-
# Copyright 2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.formats import AudioFile
from tests.plugin import PluginTestCase


class TMigratemetadata(PluginTestCase):

    def setUp(self):
        self.mod = self.modules["Migrate Metadata"]

    def tearDown(self):
        del self.mod

    def test_get_number(self):
        fn = self.mod.get_number
        song = AudioFile({'~filename': '/dev/null', 'tracknumber': '1/2',
                          'discnumber': '3'})
        self.failUnlessEqual(fn(song, 'tracknumber'), 1)
        self.failUnlessEqual(fn(song, 'discnumber'), 3)

    def test_get_number_missing(self):
        fn = self.mod.get_number
        song = AudioFile({'~filename': '/dev/null'})
        self.failUnlessEqual(fn(song, 'tracknumber'), 0)
        self.failUnlessEqual(fn(song, 'discnumber'), 0)
