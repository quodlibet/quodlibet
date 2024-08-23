# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, get_data_path
from quodlibet.formats.midi import MidiFile


class TMidiFile(TestCase):
    def setUp(self):
        self.song = MidiFile(get_data_path("test.mid"))

    def test_length(self):
        self.assertAlmostEqual(87, self.song("~#length", 0), 0)

    def test_reload(self):
        self.song["title"] = "foobar"
        self.song.reload()
        self.assertEqual(self.song("title"), "foobar")

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        self.assertEqual(self.song.can_change(), ["title"])
        self.assertTrue(self.song.can_change("title"))
        self.assertFalse(self.song.can_change("album"))

    def test_invalid(self):
        path = get_data_path("empty.xm")
        self.assertRaises(Exception, MidiFile, path)

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "MIDI")
        self.assertEqual(self.song("~codec"), "MIDI")
        self.assertEqual(self.song("~encoding"), "")
