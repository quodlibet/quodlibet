# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, get_data_path
from quodlibet.formats.aiff import AIFFFile


class TAIFFFile(TestCase):
    def setUp(self):
        self.song = AIFFFile(get_data_path("test.aiff"))

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 1.0, 1)

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 128)

    def test_format(self):
        self.assertEqual(self.song("~format"), "AIFF")

    def test_tags(self):
        self.assertEqual(self.song("artist"), "artist")
        self.assertEqual(self.song("album"), "album")
        self.assertEqual(self.song("genre"), "genre")

    def test_channels(self):
        assert self.song("~#channels") == 1

    def test_samplerate(self):
        assert self.song("~#samplerate") == 8000
