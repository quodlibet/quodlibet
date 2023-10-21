# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from tests import TestCase, get_data_path
from quodlibet.formats.wav import WAVEFile


class TWAVEFile(TestCase):

    def setUp(self):
        self.song = WAVEFile(get_data_path("test.wav"))

    def test_title_tag(self):
        self.assertEqual(self.song["title"], "test")
        self.assertTrue(isinstance(self.song["title"], str))

    def test_length(self):
        self.failUnlessAlmostEqual(self.song("~#length"), 0.227, 2)

    def test_channels(self):
        assert self.song("~#channels") == 1

    def test_samplerate(self):
        assert self.song("~#samplerate") == 11025

    def test_bitdepth(self):
        assert self.song("~#bitdepth") == 8

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        self.failUnless(self.song.can_change("artist"))

    def test_invalid(self):
        path = get_data_path("empty.xm")
        self.failUnless(os.path.exists(path))
        self.failUnlessRaises(Exception, WAVEFile, path)

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "WAVE")
        self.assertEqual(self.song("~codec"), "WAVE")
        self.assertEqual(self.song("~encoding"), "")
