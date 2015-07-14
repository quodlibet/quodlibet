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

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 0.065306, 3)

    def test_bitrate(self):
        self.failUnlessEqual(self.song("~#bitrate"), 239)

    def test_invalid(self):
        path = os.path.join(DATA_DIR, 'empty.xm')
        self.failUnless(os.path.exists(path))
        self.failUnlessRaises(Exception, MPCFile, path)


class TMPCSV8File(TestCase):

    def setUp(self):
        self.song = MPCFile(os.path.join(DATA_DIR, 'silence-44-s.sv8.mpc'))

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 3.684716, 3)

    def test_bitrate(self):
        self.failUnlessEqual(self.song("~#bitrate"), 1)
