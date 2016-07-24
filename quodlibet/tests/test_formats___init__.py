# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys
import os
import pickle

from tests import TestCase, DATA_DIR
from .helper import capture_output, temp_filename

from quodlibet import formats
from quodlibet.formats import AudioFile
from quodlibet import config


class TFormats(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_presence(self):
        self.failUnless(formats.aac)
        self.failUnless(formats.aiff)
        self.failUnless(formats.midi)
        self.failUnless(formats.mod)
        self.failUnless(formats.monkeysaudio)
        self.failUnless(formats.mp3)
        self.failUnless(formats.mp4)
        self.failUnless(formats.mpc)
        self.failUnless(formats.spc)
        self.failUnless(formats.trueaudio)
        self.failUnless(formats.vgm)
        self.failUnless(formats.wav)
        self.failUnless(formats.wavpack)
        self.failUnless(formats.wma)
        self.failUnless(formats.xiph)

    def test_loaders(self):
        self.failUnless(formats.loaders[".mp3"] is formats.mp3.MP3File)

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
            self.assertTrue(stderr.getvalue())

        # unknown extension
        with capture_output() as (stdout, stderr):
            song = formats.MusicFile(os.path.join(DATA_DIR, "nope.xxx"))
            self.assertFalse(song)
            self.assertFalse(stderr.getvalue())


class TPickle(TestCase):

    def setUp(self):
        types = formats.types
        instances = []
        for t in types:
            instances.append(AudioFile.__new__(t))

        self.PICKLE = pickle.dumps(instances, 1)

    def test_unpickle(self):
        self.assertEqual(len(pickle.loads(self.PICKLE)), len(formats.types))

    def test_load_items(self):
        from quodlibet.library.libraries import load_items

        with temp_filename() as filename:
            with open(filename, "wb") as h:
                h.write(self.PICKLE)

            self.assertEqual(len(load_items(filename)), len(formats.types))

    def test_dump_items(self):
        from quodlibet.library.libraries import dump_items, load_items

        types = formats.types
        instances = []
        for t in types:
            instances.append(AudioFile.__new__(t))

        with temp_filename() as filename:
            dump_items(filename, instances)
            self.assertEqual(len(load_items(filename)), len(formats.types))

    def test_unpickle_save(self):
        from quodlibet.library.libraries import unpickle_save

        items = unpickle_save(self.PICKLE, [])
        self.assertEqual(len(items), len(formats.types))

        broken = self.PICKLE.replace(b"SPCFile", b"FooFile")
        items = unpickle_save(broken, [])
        self.assertEqual(len(items), len(formats.types) - 1)

        broken = self.PICKLE.replace(b"formats.spc", b"formats.foo")
        items = unpickle_save(broken, [])
        self.assertEqual(len(items), len(formats.types) - 1)
