# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase, add

import os
import sys

from quodlibet.qltk.edittags import *
from quodlibet.library import SongLibrary
import quodlibet.config

class TEditTags(TestCase):
    def setUp(self):
        quodlibet.config.init()
    def tearDown(self):
        quodlibet.config.quit()

    def test_items(self):
        SplitValues("foo", "bar").destroy()
        SplitDisc("foo", "bar").destroy()
        SplitTitle("foo", "bar").destroy()
        SplitArranger("foo", "bar").destroy()

    def test_addtag_dialog(self):
        lib = SongLibrary()
        AddTagDialog(None, ["artist"], lib).destroy()

add(TEditTags)
