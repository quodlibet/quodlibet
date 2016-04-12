# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet import config
from tests import TestCase
from quodlibet.qltk.data_editors import TagListEditor


class TMultiStringEditor(TestCase):

    def setUp(self):
        config.init()

    def test_no_strings(self):
        mse = TagListEditor("title")
        self.failUnlessEqual(mse.get_strings(), [])
        self.failUnlessEqual(mse.get_title(), "title")
        mse.destroy()

    def test_defaulting(self):
        defaults = ["one", "two three"]
        mse = TagListEditor("title", defaults)
        self.failUnlessEqual(mse.get_strings(), defaults)
        mse.destroy()

    def tearDown(self):
        config.quit()
