# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from tests import TestCase, add
from quodlibet.formats.midi import MidiFile


class TMidiFile(TestCase):
    def setUp(self):
        self.song = MidiFile(os.path.join('tests', 'data', 'test.mid'))

    def test_length(self):
        self.failUnlessAlmostEqual(87, self.song("~#length", 0), 0)

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
        path = os.path.join('tests', 'data', 'empty.xm')
        self.failUnlessRaises(Exception, MidiFile, path)

add(TMidiFile)
