# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from tests import TestCase, DATA_DIR
from quodlibet.formats.aiff import AIFFFile


class TAIFFFile(TestCase):

    def setUp(self):
        self.song = AIFFFile(os.path.join(DATA_DIR, 'test.aiff'))

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 1.0, 1)

    def test_bitrate(self):
        self.failUnlessEqual(self.song("~#bitrate"), 128)

    def test_format(self):
        self.assertEqual(self.song("~format"), "AIFF")

    def test_tags(self):
        self.assertEqual(self.song("artist"), "artist")
        self.assertEqual(self.song("album"), "album")
        self.assertEqual(self.song("genre"), "genre")
