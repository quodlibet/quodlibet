# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from tests import TestCase

from senf import fsnative

from quodlibet.qltk.renamefiles import (SpacesToUnderscores,
    StripWindowsIncompat)
from quodlibet.qltk.renamefiles import StripDiacriticals, StripNonASCII
from quodlibet.qltk.renamefiles import Lowercase


class TFilter(TestCase):
    def setUp(self):
        self.c = self.Kind()

    def tearDown(self):
        self.c.destroy()


class TFilterMixin(object):

    def test_empty(self):
        empty = fsnative(u"")
        v = self.c.filter(empty, empty)
        self.failUnlessEqual(v, empty)
        self.failUnless(isinstance(v, fsnative))

    def test_safe(self):
        empty = fsnative(u"")
        safe = fsnative(u"safe")
        self.failUnlessEqual(self.c.filter(empty, safe), safe)


class TSpacesToUnderscores(TFilter):
    Kind = SpacesToUnderscores

    def test_conv(self):
        self.failUnlessEqual(self.c.filter("", "foo bar "), "foo_bar_")


class TStripWindowsIncompat(TFilter):
    Kind = StripWindowsIncompat

    def test_conv(self):
        if os.name == "nt":
            self.failUnlessEqual(
                self.c.filter(u"", u'foo\\:*?;"<>|/'), u"foo\\_________")
        else:
            self.failUnlessEqual(
                self.c.filter("", 'foo\\:*?;"<>|/'), "foo_________/")

    def test_type(self):
        empty = fsnative(u"")
        self.assertTrue(isinstance(self.c.filter(empty, empty), fsnative))

    def test_ends_with_dots_or_spaces(self):
        empty = fsnative(u"")
        v = self.c.filter(empty, fsnative(u'foo. . '))
        self.failUnlessEqual(v, fsnative(u"foo. ._"))
        self.assertTrue(isinstance(v, fsnative))

        if os.name == "nt":
            self.failUnlessEqual(
                self.c.filter(empty, u'foo. \\bar .'), u"foo._\\bar _")
        else:
            self.failUnlessEqual(
                self.c.filter(empty, u'foo. /bar .'), "foo._/bar _")


class TStripDiacriticals(TFilter):
    Kind = StripDiacriticals

    def test_conv(self):
        empty = fsnative(u"")
        test = fsnative(u"\u00c1 test")
        out = fsnative(u"A test")
        v = self.c.filter(empty, test)
        self.failUnlessEqual(v, out)
        self.failUnless(isinstance(v, fsnative))


class TStripNonASCII(TFilter):
    Kind = StripNonASCII

    def test_conv(self):
        empty = fsnative(u"")
        in_ = fsnative(u"foo \u00c1 \u1234")
        out = fsnative(u"foo _ _")
        v = self.c.filter(empty, in_)
        self.failUnlessEqual(v, out)
        self.failUnless(isinstance(v, fsnative))


class TLowercase(TFilter):
    Kind = Lowercase

    def test_conv(self):
        empty = fsnative(u"")

        v = self.c.filter(empty, fsnative(u"foobar baz"))
        self.failUnlessEqual(v, fsnative(u"foobar baz"))
        self.failUnless(isinstance(v, fsnative))

        v = self.c.filter(empty, fsnative(u"Foobar.BAZ"))
        self.failUnlessEqual(v, fsnative(u"foobar.baz"))
        self.failUnless(isinstance(v, fsnative))
