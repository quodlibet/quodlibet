# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.qltk.exfalsowindow import ExFalsoWindow
from quodlibet.library import SongLibrary
import quodlibet.config


class TExFalsoWindow(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.ef = ExFalsoWindow(SongLibrary())

    def test_nothing(self):
        self.failUnless(self.ef.get_child())

    def tearDown(self):
        self.ef.destroy()
        quodlibet.config.quit()
