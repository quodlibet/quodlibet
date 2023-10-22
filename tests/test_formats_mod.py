# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, skipUnless, get_data_path

from quodlibet.formats.mod import ModFile, extensions


@skipUnless(extensions, "ModPlug missing")
class TModFile(TestCase):
    def setUp(self):
        self.song = ModFile(get_data_path("empty.xm"))

    def test_length(self):
        self.assertEqual(self.song("~#length", 0), 0)

    def test_title(self):
        self.assertEqual(self.song["title"], "test song")

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "MOD/XM/IT")
        self.assertEqual(self.song("~codec"), "MOD/XM/IT")
        self.assertEqual(self.song("~encoding"), "")
