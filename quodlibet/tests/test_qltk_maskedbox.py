# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet import config
from quodlibet.qltk.maskedbox import MaskedBox
from quodlibet.library import SongFileLibrary


class TMaskedBox(TestCase):
    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test(self):
        lib = SongFileLibrary()
        MaskedBox(lib).destroy()
