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
        self.song = VgmFile(get_data_path("test.vgm"))

    def test_length(self):
        self.assertAlmostEqual(2.81, self.song("~#length", 0), 1)

    def test_reload(self):
        self.song["title"] = "foobar"
        self.song.reload()
        self.assertEqual(self.song("title"), "Chaos Emerald")

    def test_gd3_tags(self):
        expected_tags = {
            "title": "Chaos Emerald",
            "album": "Sonic the Hedgehog\nソニック・ザ・ヘッジホッグ",
            "console": "Sega Mega Drive\nセガメガドライブ",
            "artist": "Masato Nakamura\n中村正人",
            "date": "1991"
        }

        for k, v in expected_tags.items():
            self.assertEqual(self.song[k], v)

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        self.assertEqual(self.song.can_change(), ["title"])
        assert self.song.can_change("title")
        assert not self.song.can_change("album")

    def test_invalid(self):
        path = get_data_path("empty.xm")
        self.assertRaises(Exception, VgmFile, path)

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "VGM")
        self.assertEqual(self.song("~codec"), "VGM")
        self.assertEqual(self.song("~encoding"), "")
