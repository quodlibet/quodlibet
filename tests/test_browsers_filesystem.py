# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.browsers.filesystem import FileSystem
from quodlibet.library import SongLibrary
import quodlibet.config


class TFileSystem(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.bar = FileSystem(SongLibrary())

    def test_can_filter(self):
        for key in ["foo", "title", "fake~key", "~woobar", "~#huh"]:
            self.failIf(self.bar.can_filter(key))
        self.failUnless(self.bar.can_filter("~dirname"))

    def tearDown(self):
        self.bar.destroy()
        quodlibet.config.quit()
