# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys
import os
import pickle

from tests import TestCase, DATA_DIR
from helper import capture_output, temp_filename

from quodlibet import formats
from quodlibet.formats._audio import AudioFile
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


class TPickle(TestCase):

    # protocol 1 pickle of all types (created by test_pickle below)
    PICKLE = (
        b']q\x00(ccopy_reg\n_reconstructor\nq\x01(cquodlibet.formats.vgm'
        b'\nVgmFile\nq\x02c__builtin__\ndict\nq\x03}q\x04tq\x05Rq\x06h\x01'
        b'(cquodlibet.formats.monkeysaudio\nMonkeysAudioFile\nq\x07h\x03}q'
        b'\x08tq\tRq\nh\x01(cquodlibet.formats.mpc\nMPCFile\nq\x0bh\x03}q'
        b'\x0ctq\rRq\x0eh\x01(cquodlibet.formats.midi\nMidiFile\nq\x0fh'
        b'\x03}q\x10tq\x11Rq\x12h\x01(cquodlibet.formats.wavpack\nWavpack'
        b'File\nq\x13h\x03}q\x14tq\x15Rq\x16h\x01(cquodlibet.formats.true'
        b'audio\nTrueAudioFile\nq\x17h\x03}q\x18tq\x19Rq\x1ah\x01(cquodli'
        b'bet.formats.mp4\nMP4File\nq\x1bh\x03}q\x1ctq\x1dRq\x1eh\x01(cquo'
        b'dlibet.formats.xiph\nOggFLACFile\nq\x1fh\x03}q tq!Rq"h\x01(cquod'
        b'libet.formats.xiph\nOggSpeexFile\nq#h\x03}q$tq%Rq&h\x01(cquodlib'
        b'et.formats.xiph\nOggOpusFile\nq\'h\x03}q(tq)Rq*h\x01(cquodlibet'
        b'.formats.xiph\nOggFile\nq+h\x03}q,tq-Rq.h\x01(cquodlibet.formats'
        b'.xiph\nFLACFile\nq/h\x03}q0tq1Rq2h\x01(cquodlibet.formats.xiph\n'
        b'OggTheoraFile\nq3h\x03}q4tq5Rq6h\x01(cquodlibet.formats.wav\nWAV'
        b'EFile\nq7h\x03}q8tq9Rq:h\x01(cquodlibet.formats.wma\nWMAFile\nq;'
        b'h\x03}q<tq=Rq>h\x01(cquodlibet.formats.spc\nSPCFile\nq?h\x03}q@t'
        b'qARqBh\x01(cquodlibet.formats.mp3\nMP3File\nqCh\x03}qDtqERqFh'
        b'\x01(cquodlibet.formats.mod\nModFile\nqGh\x03}qHtqIRqJe.')

    def test_pickle(self):
        types = formats.types
        instances = []
        for t in types:
            instances.append(AudioFile.__new__(t))

        with temp_filename() as filename:
            with open(filename, "wb") as h:
                pickle.dump(instances, h, 1)

            with open(filename, "rb") as h:
                self.assertEqual(len(pickle.load(h)), len(formats.types))

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
