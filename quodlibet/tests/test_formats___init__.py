# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

from tests import TestCase, add
from quodlibet import formats

class TFormats(TestCase):
    def test_presence(self):
        self.failUnless(formats.midi)
        self.failUnless(formats.mod)
        self.failUnless(formats.monkeysaudio)
        self.failUnless(formats.mpc)
        self.failUnless(formats.mp3)
        self.failUnless(formats.mp4)
        self.failUnless(formats.spc)
        self.failUnless(formats.trueaudio)

    def test_infos(self):
        self.failUnless(formats._infos[".mp3"] is formats.mp3.MP3File)

    def test_migration(self):
        self.failUnless(formats.mp3 is sys.modules["quodlibet.formats.mp3"])
        self.failUnless(formats.mp3 is sys.modules["quodlibet/formats/mp3"])
        self.failUnless(formats.mp3 is sys.modules["formats.mp3"])

        self.failUnless(formats.xiph is sys.modules["formats.flac"])
        self.failUnless(formats.xiph is sys.modules["formats.oggvorbis"])
add(TFormats)
