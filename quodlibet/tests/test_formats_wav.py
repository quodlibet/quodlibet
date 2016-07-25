# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from tests import TestCase, DATA_DIR
from quodlibet.formats.wav import WAVEFile
from quodlibet.compat import text_type


class TWAVEFile(TestCase):

    def setUp(self):
        self.song = WAVEFile(os.path.join(DATA_DIR, 'test.wav'))

    def test_title_tag(self):
        self.assertEqual(self.song["title"], "test")
        self.assertTrue(isinstance(self.song["title"], text_type))

    def test_length(self):
        self.failUnlessAlmostEqual(self.song("~#length"), 0.227, 2)

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        self.failUnless(self.song.can_change("artist"))

    def test_invalid(self):
        path = os.path.join(DATA_DIR, 'empty.xm')
        self.failUnless(os.path.exists(path))
        self.failUnlessRaises(Exception, WAVEFile, path)

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "WAVE")
        self.assertEqual(self.song("~codec"), "WAVE")
        self.assertEqual(self.song("~encoding"), "")
