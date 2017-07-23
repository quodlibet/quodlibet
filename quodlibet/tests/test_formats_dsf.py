# -*- coding: utf-8 -*-
# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, get_data_path, skipUnless
from quodlibet.formats.dsf import DSFFile, extensions


@skipUnless(extensions, "too old mutagen")
class TDSFFile(TestCase):

    def setUp(self):
        self.song1 = DSFFile(get_data_path("with-id3.dsf"))
        self.song2 = DSFFile(get_data_path("without-id3.dsf"))
        self.song3 = DSFFile(get_data_path("2822400-1ch-0s-silence.dsf"))
        self.song4 = DSFFile(get_data_path("5644800-2ch-s01-silence.dsf"))

    def test_length(self):
        self.assertAlmostEqual(self.song1("~#length"), 0.0, 1)
        self.assertAlmostEqual(self.song2("~#length"), 0.0, 1)
        self.assertAlmostEqual(self.song3("~#length"), 0.0, 1)
        self.assertAlmostEqual(self.song4("~#length"), 0.01, 2)

    def test_bitrate(self):
        self.failUnlessEqual(self.song1("~#bitrate"), 2822)
        self.failUnlessEqual(self.song2("~#bitrate"), 2822)
        self.failUnlessEqual(self.song3("~#bitrate"), 2822)
        self.failUnlessEqual(self.song4("~#bitrate"), 11289)

    def test_format(self):
        self.assertEqual(self.song1("~format"), "DSF")

    def test_tags(self):
        self.assertEqual(self.song1("title"), "DSF title")

    def test_channels(self):
        assert self.song1("~#channels") == 1
        assert self.song2("~#channels") == 1
        assert self.song3("~#channels") == 1
        assert self.song4("~#channels") == 2
