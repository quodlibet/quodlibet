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
        b']q\x00(ccopy_reg\n_reconstructor\nq\x01(cquodlibet.formats.vgm\nVgm'
        b'File\nq\x02c__builtin__\ndict\nq\x03}q\x04tq\x05Rq\x06h\x01(cquodli'
        b'bet.formats.monkeysaudio\nMonkeysAudioFile\nq\x07h\x03}q\x08tq\tRq'
        b'\nh\x01(cquodlibet.formats.mpc\nMPCFile\nq\x0bh\x03}q\x0ctq\rRq\x0eh'
        b'\x01(cquodlibet.formats.aac\nAACFile\nq\x0fh\x03}q\x10tq\x11Rq'
        b'\x12h\x01(cquodlibet.formats.midi\nMidiFile\nq\x13h\x03}q\x14'
        b'tq\x15Rq\x16h\x01(cquodlibet.formats.wavpack\nWavpackFile\nq\x17'
        b'h\x03}q\x18tq\x19Rq\x1ah\x01(cquodlibet.formats.trueaudio\nTrueAudio'
        b'File\nq\x1bh\x03}q\x1ctq\x1dRq\x1eh\x01(cquodlibet.formats.mp4\nMP4'
        b'File\nq\x1fh\x03}q tq!Rq"h\x01(cquodlibet.formats.xiph\nOggFLACFile'
        b'\nq#h\x03}q$tq%Rq&h\x01(cquodlibet.formats.xiph\nOggSpeexFile\nq\'h'
        b'\x03}q(tq)Rq*h\x01(cquodlibet.formats.xiph\nOggOpusFile\nq+h\x03}q,'
        b'tq-Rq.h\x01(cquodlibet.formats.xiph\nOggFile\nq/h\x03}q0tq1Rq2h\x01'
        b'(cquodlibet.formats.xiph\nFLACFile\nq3h\x03}q4tq5Rq6h\x01(cquodlibet'
        b'.formats.xiph\nOggTheoraFile\nq7h\x03}q8tq9Rq:h\x01(cquodlibet.forma'
        b'ts.wav\nWAVEFile\nq;h\x03}q<tq=Rq>h\x01(cquodlibet.formats.wma\nWMA'
        b'File\nq?h\x03}q@tqARqBh\x01(cquodlibet.formats.spc\nSPCFile\nqCh\x03'
        b'}qDtqERqFh\x01(cquodlibet.formats.mp3\nMP3File\nqGh\x03}qHtqIRqJh'
        b'\x01(cquodlibet.formats.remote\nRemoteFile\nqKh\x03}qLtqMRqNh\x01(cq'
        b'uodlibet.formats.mod\nModFile\nqOh\x03}qPtqQRqRe.')

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
