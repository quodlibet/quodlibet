# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from quodlibet import app
from tests import TestCase, destroy_fake_app, init_fake_app

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.info import SongInfo
from quodlibet.library import SongLibrary

FILENAME = "test-pattern"
SOME_PATTERN = "foo\n[big]<title>[/big] - <artist>"


class FakePatternEdit(object):
    @property
    def text(self):
        return SOME_PATTERN


class TSongInfo(TestCase):
    def setUp(self):
        init_fake_app()
        self.info = SongInfo(SongLibrary(), NullPlayer(), FILENAME)

    def test_save(self):
        fake_edit = FakePatternEdit()
        self.info._on_set_pattern(None, fake_edit, app.player)
        with open(FILENAME, "r") as f:
            contents = f.read()
            self.failUnlessEqual(contents, SOME_PATTERN + "\n")
        os.unlink(FILENAME)

    def tearDown(self):
        destroy_fake_app()
        self.info.destroy()
