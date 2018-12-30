# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.formats import DUMMY_SONG
from quodlibet.qltk._editutils import FilterCheckButton, \
    OverwriteWarning, WriteFailedError, FilterPluginBox, EditingPluginHandler


class FCB(FilterCheckButton):
    _section = _key = _label = "foo"


class FCB2(FCB):
    _order = 1.0


class FCB3(FCB):
    _order = 1.2


class FCB4(FCB):
    _order = 1.3


class FCB5(FCB):
    _order = 1.3


class FCB1(FCB):
    _order = 1.4


class TFilterCheckButton(TestCase):
    def setUp(self):
        self.fcb1 = FCB1()
        self.fcb2 = FCB2()
        self.fcb3 = FCB3()
        self.fcb4 = FCB4()
        self.fcb5 = FCB5()

    def test_filter(self):
        self.failUnlessRaises(NotImplementedError, self.fcb1.filter, "", "")

    def test_filter_list(self):
        self.failUnlessRaises(
            NotImplementedError, self.fcb1.filter_list, [""], [""])

    def test_cmp(self):
        l = [self.fcb1, self.fcb2, self.fcb3, self.fcb4, self.fcb5]
        l.sort()
        self.failUnlessEqual(
            l, [self.fcb2, self.fcb3, self.fcb4, self.fcb5, self.fcb1])

    def tearDown(self):
        for cb in [self.fcb1, self.fcb2, self.fcb3, self.fcb4, self.fcb5]:
            cb.destroy()


class TEditDialogs(TestCase):

    def test_overwrite(self):
        OverwriteWarning(None, DUMMY_SONG).destroy()

    def test_write_failed(self):
        WriteFailedError(None, DUMMY_SONG).destroy()


class TFilterPluginBox(TestCase):

    def test_main(self):
        handler = EditingPluginHandler()
        x = FilterPluginBox(handler)
        self.assertEqual(x.filters, [])
        x.destroy()
