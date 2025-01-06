# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from mutagen.aac import AAC

from quodlibet.formats.aac import AACFile

from . import TestCase, get_data_path, skipUnless
from .helper import get_temp_copy


class _TAACFile(TestCase):
    NAME = None

    def setUp(self):
        self.f = get_temp_copy(get_data_path(self.NAME))
        self.song = AACFile(self.f)

    def tearDown(self):
        os.unlink(self.f)


class _TAACFileMixin:
    def test_basic(self):
        self.song["title"] = "SomeTestValue"
        self.song.write()
        self.song.reload()
        self.assertEqual(self.song("title"), "SomeTestValue")

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        assert self.song.can_change("title")
        assert not self.song.can_change("foobar")
        assert "title" in self.song.can_change()

    def test_can_multiple_values(self):
        self.assertEqual(self.song.can_multiple_values(), True)
        assert self.song.can_multiple_values("title")

    def test_invalid(self):
        path = get_data_path("empty.xm")
        assert os.path.exists(path)
        self.assertRaises(Exception, AACFile, path)

    def test_format_codec(self):
        self.assertEqual(self.song("~format"), "AAC")
        self.assertEqual(self.song("~codec"), "AAC")
        self.assertEqual(self.song("~encoding"), "")

    def test_channels(self):
        assert self.song("~#channels") == 2


@skipUnless(AAC, "too old mutagen")
class TADTSFile(_TAACFile, _TAACFileMixin):
    NAME = "empty.aac"

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 3.7, 2)

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 3)

    def test_samplerate(self):
        assert self.song("~#samplerate") == 44100


@skipUnless(AAC, "too old mutagen")
class TADIFFile(_TAACFile, _TAACFileMixin):
    NAME = "adif.aac"

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 0.25, 2)

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 128)

    def test_samplerate(self):
        assert self.song("~#samplerate") == 48000
