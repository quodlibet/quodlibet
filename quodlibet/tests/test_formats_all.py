# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from tests import TestCase, DATA_DIR

from quodlibet.formats import MusicFile, AudioFileError, EmbeddedImage

from .helper import get_temp_copy


FILES = [
    os.path.join(DATA_DIR, "empty.ogg"),
    os.path.join(DATA_DIR, "empty.flac"),
    os.path.join(DATA_DIR, "silence-44-s.mp3"),
    os.path.join(DATA_DIR, "silence-44-s.mpc"),
    os.path.join(DATA_DIR, "test.wma"),
    os.path.join(DATA_DIR, "coverart.wv"),
    os.path.join(DATA_DIR, "test.m4a"),
    os.path.join(DATA_DIR, "empty.opus"),
    os.path.join(DATA_DIR, "silence-44-s.tta"),
    os.path.join(DATA_DIR, "empty.aac"),
    os.path.join(DATA_DIR, "test.mid"),
    os.path.join(DATA_DIR, "test.wav"),
    os.path.join(DATA_DIR, "silence-44-s.ape"),
    os.path.join(DATA_DIR, "test.vgm"),
    os.path.join(DATA_DIR, "silence-44-s.spx"),
    os.path.join(DATA_DIR, "test.spc"),
]


class TAudioFileAllBase(object):

    FILE = None

    def setUp(self):
        self.filename = get_temp_copy(self.FILE)
        self.song = MusicFile(self.filename)

    def tearDown(self):
        try:
            os.remove(self.filename)
        except OSError:
            pass

    def test_clear_images_noent(self):
        os.remove(self.filename)
        self.assertRaises(AudioFileError, self.song.clear_images)

    def test_set_image_noent(self):
        os.remove(self.filename)
        image = EmbeddedImage(None, "image/png")
        self.assertRaises(AudioFileError, self.song.set_image, image)

    def test_get_primary_image_noent(self):
        os.remove(self.filename)
        self.assertTrue(self.song.get_primary_image() is None)

    def test_get_images_noent(self):
        os.remove(self.filename)
        self.assertEqual(self.song.get_images(), [])

    def test_write_noent(self):
        os.remove(self.filename)
        try:
            self.song.write()
        except AudioFileError:
            pass

    def test_load_noent(self):
        os.remove(self.filename)
        self.assertRaises(AudioFileError, type(self.song), self.filename)

    @classmethod
    def create_tests(cls):
        for i, file_ in enumerate(FILES):
            new_type = type(cls.__name__ + str(i),
                            (cls, TestCase), {"FILE": file_})
            assert new_type.__name__ not in globals()
            globals()[new_type.__name__] = new_type


TAudioFileAllBase.create_tests()
