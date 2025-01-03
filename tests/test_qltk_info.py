# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import tempfile

from quodlibet import app
from tests import TestCase, destroy_fake_app, init_fake_app

from quodlibet.player.nullbe import NullPlayer
from quodlibet.qltk.info import SongInfo
from quodlibet.library import SongLibrary


SOME_PATTERN = "foo\n[big]<title>[/big] - <artist>"


class FakePatternEdit:
    @property
    def text(self):
        return SOME_PATTERN


class TSongInfo(TestCase):
    def setUp(self):
        init_fake_app()
        fd, self.filename = tempfile.mkstemp()
        os.close(fd)
        self.info = SongInfo(SongLibrary(), NullPlayer(), self.filename)

    def test_save(self):
        fake_edit = FakePatternEdit()
        self.info._on_set_pattern(None, fake_edit, app.player)
        with open(self.filename) as f:
            contents = f.read()
            self.assertEqual(contents, SOME_PATTERN + "\n")

    def tearDown(self):
        destroy_fake_app()
        self.info.destroy()
        os.unlink(self.filename)
