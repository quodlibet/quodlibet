# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys
import os

from tests import TestCase, DATA_DIR
from helper import capture_output

from quodlibet import formats
from quodlibet import config


class TFormats(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

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

    def test_filter(self):
        self.assertTrue(formats.filter("foo.mp3"))
        self.assertFalse(formats.filter("foo.doc"))
        self.assertFalse(formats.filter("foomp3"))

    def test_music_file(self):
        path = os.path.join(DATA_DIR, 'silence-44-s.mp3')
        self.assertTrue(formats.MusicFile(path))

        # non existing
        with capture_output() as (stdout, stderr):
            song = formats.MusicFile(os.path.join(DATA_DIR, "nope.mp3"))
            self.assertFalse(song)
            self.assertTrue("Error" in stderr.getvalue())

        # unknown extension
        with capture_output() as (stdout, stderr):
            song = formats.MusicFile(os.path.join(DATA_DIR, "nope.xxx"))
            self.assertFalse(song)
            self.assertTrue("extension" in stderr.getvalue())
