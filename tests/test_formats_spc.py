# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from tests import TestCase, get_data_path
from quodlibet.formats.spc import SPCFile


class TSPCFile(TestCase):
    def setUp(self):
        self.song = SPCFile(get_data_path("test.spc"))

    def test_tags(self):
        tags = {
            "title": "Game Select",
            "artist": "Koji Kondo",
            "album": "Super Mario All-Stars",
            "dumper": "Datschge",
        }

        for k, v in tags.items():
            self.failUnlessEqual(self.song[k], v)

    def test_length(self):
        self.failUnlessEqual(self.song("~#length"), 25)

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        self.failUnless(self.song.can_change("title"))

    def test_invalid(self):
        path = get_data_path("empty.xm")
        self.failUnless(os.path.exists(path))
        self.failUnlessRaises(Exception, SPCFile, path)

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "SPC700")
        self.assertEqual(self.song("~codec"), "SPC700")
        self.assertEqual(self.song("~encoding"), "")
