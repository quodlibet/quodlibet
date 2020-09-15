# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from tests import TestCase, get_data_path

from quodlibet.formats import MusicFile, AudioFileError, EmbeddedImage

from .helper import get_temp_copy


FILES = [
    get_data_path("empty.ogg"),
    get_data_path("empty.flac"),
    get_data_path("silence-44-s.mp3"),
    get_data_path("silence-44-s.mpc"),
    get_data_path("test.wma"),
    get_data_path("coverart.wv"),
    get_data_path("test.m4a"),
    get_data_path("empty.opus"),
    get_data_path("silence-44-s.tta"),
    get_data_path("empty.aac"),
    get_data_path("test.mid"),
    get_data_path("test.wav"),
    get_data_path("silence-44-s.ape"),
    get_data_path("test.vgm"),
    get_data_path("silence-44-s.spx"),
    get_data_path("test.spc"),
]


class TAudioFileAllBase:

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
