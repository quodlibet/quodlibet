# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from tests import TestCase, get_data_path
from quodlibet.formats.mpc import MPCFile


class TMPCFile(TestCase):

    def setUp(self):
        self.song = MPCFile(get_data_path("silence-44-s.mpc"))
        self.song2 = MPCFile(get_data_path("silence-44-s.sv8.mpc"))

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 0.065306, 3)
        self.assertAlmostEqual(self.song2("~#length"), 3.684716, 3)

    def test_channels(self):
        assert self.song("~#channels") == 2
        assert self.song2("~#channels") == 2

    def test_samplerate(self):
        assert self.song("~#samplerate") == 44100
        assert self.song2("~#samplerate") == 44100

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 239)
        self.assertEqual(self.song2("~#bitrate"), 1)

    def test_invalid(self):
        path = get_data_path("empty.xm")
        assert os.path.exists(path)
        self.assertRaises(Exception, MPCFile, path)

    def test_format(self):
        self.assertEqual(self.song("~format"), "Musepack")
        self.assertEqual(self.song2("~format"), "Musepack")

    def test_codec(self):
        self.assertEqual(self.song("~codec"), "Musepack SV7")
        self.assertEqual(self.song2("~codec"), "Musepack SV8")

    def test_encoding(self):
        self.assertEqual(self.song("~encoding"), "")
        self.assertEqual(self.song2("~encoding"), "")
