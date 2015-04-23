# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import shutil

from tests import TestCase, DATA_DIR, mkstemp, skipUnless
from quodlibet.formats.aac import AACFile

try:
    from mutagen.aac import AAC
except ImportError:
    AAC = None


class _TAACFile(TestCase):

    NAME = None

    def setUp(self):
        fd, self.f = mkstemp(".aac")
        os.close(fd)
        shutil.copy(os.path.join(DATA_DIR, self.NAME), self.f)
        self.song = AACFile(self.f)

    def tearDown(self):
        os.unlink(self.f)


class _TAACFileMixin(object):

    def test_basic(self):
        self.song["title"] = u"SomeTestValue"
        self.song.write()
        self.song.reload()
        self.assertEqual(self.song("title"), u"SomeTestValue")

    def test_write(self):
        self.song.write()

    def test_can_change(self):
        self.assertTrue(self.song.can_change("title"))
        self.assertFalse(self.song.can_change("foobar"))
        self.assertTrue("title" in self.song.can_change())

    def test_can_multiple_values(self):
        self.assertEqual(self.song.can_multiple_values(), True)
        self.assertTrue(self.song.can_multiple_values("title"))

    def test_invalid(self):
        path = os.path.join(DATA_DIR, 'empty.xm')
        self.assertTrue(os.path.exists(path))
        self.assertRaises(Exception, AACFile, path)


@skipUnless(AAC, "too old mutagen")
class TADTSFile(_TAACFile, _TAACFileMixin):

    NAME = "empty.aac"

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 3.7, 2)

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 3)


@skipUnless(AAC, "too old mutagen")
class TADIFFile(_TAACFile, _TAACFileMixin):

    NAME = "adif.aac"

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 0.25, 2)

    def test_bitrate(self):
        self.assertEqual(self.song("~#bitrate"), 128)
