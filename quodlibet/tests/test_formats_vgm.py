# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, get_data_path
from quodlibet.formats.vgm import VgmFile


class TVgmFile(TestCase):
    def setUp(self):
        self.song = VgmFile(get_data_path('test.vgm'))

    def test_length(self):
        self.failUnlessAlmostEqual(2.81, self.song("~#length", 0), 1)

    def test_reload(self):
        self.song["title"] = "foobar"
        self.song.reload()
        self.failUnlessEqual(self.song("title"), "foobar")

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        self.failUnlessEqual(self.song.can_change(), ["title"])
        self.failUnless(self.song.can_change("title"))
        self.failIf(self.song.can_change("album"))

    def test_invalid(self):
        path = get_data_path('empty.xm')
        self.failUnlessRaises(Exception, VgmFile, path)

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "VGM")
        self.assertEqual(self.song("~codec"), "VGM")
        self.assertEqual(self.song("~encoding"), "")
