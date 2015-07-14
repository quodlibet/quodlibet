# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from tests import TestCase, DATA_DIR
from quodlibet.formats.mp3 import MP3File
from quodlibet import config


class TMP3File(TestCase):

    def setUp(self):
        config.init()
        self.song = MP3File(os.path.join(DATA_DIR, 'silence-44-s.mp3'))

    def tearDown(self):
        config.quit()

    def test_length(self):
        self.assertAlmostEqual(self.song("~#length"), 3.0, 1)

    def test_bitrate(self):
        self.failUnlessEqual(self.song("~#bitrate"), 32)
