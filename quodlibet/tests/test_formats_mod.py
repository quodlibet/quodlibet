# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase, skipUnless, DATA_DIR

import os

from quodlibet.formats.mod import ModFile, extensions


@skipUnless(extensions, "ModPlug missing")
class TModFile(TestCase):
    def setUp(self):
        self.song = ModFile(os.path.join(DATA_DIR, 'empty.xm'))

    def test_length(self):
        self.failUnlessEqual(0, self.song("~#length", 0))

    def test_title(self):
        self.failUnlessEqual("test song", self.song["title"])

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "MOD/XM/IT")
        self.assertEqual(self.song("~codec"), "MOD/XM/IT")
        self.assertEqual(self.song("~encoding"), "")
