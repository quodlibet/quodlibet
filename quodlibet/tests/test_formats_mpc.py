# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from tests import TestCase, DATA_DIR
from quodlibet.formats.mpc import MPCFile


class TMPCFile(TestCase):

    def setUp(self):
        self.song = MPCFile(os.path.join(DATA_DIR, 'silence-44-s.mpc'))
        self.song2 = MPCFile(os.path.join(DATA_DIR, 'silence-44-s.sv8.mpc'))

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 0.065306, 3)
        self.assertAlmostEqual(self.song2("~#length"), 3.684716, 3)

    def test_bitrate(self):
        self.failUnlessEqual(self.song("~#bitrate"), 239)
        self.failUnlessEqual(self.song2("~#bitrate"), 1)

    def test_invalid(self):
        path = os.path.join(DATA_DIR, 'empty.xm')
        self.failUnless(os.path.exists(path))
        self.failUnlessRaises(Exception, MPCFile, path)

    def test_format(self):
        self.assertEqual(self.song("~format"), "Musepack")
        self.assertEqual(self.song2("~format"), "Musepack")

    def test_codec(self):
        self.assertEqual(self.song("~codec"), "Musepack SV7")
        self.assertEqual(self.song2("~codec"), "Musepack SV8")

    def test_encoding(self):
        self.assertEqual(self.song("~encoding"), "")
        self.assertEqual(self.song2("~encoding"), "")
