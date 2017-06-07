# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from tests import TestCase

from senf import fsnative

from quodlibet.qltk.renamefiles import StripDiacriticals, StripNonASCII, \
    Lowercase, SpacesToUnderscores, StripWindowsIncompat
from quodlibet.compat import text_type


class TFilter(TestCase):
    def setUp(self):
        self.c = self.Kind()

    def tearDown(self):
        self.c.destroy()


class TFilterMixin(object):

    def test_mix_empty(self):
        empty = fsnative(u"")
        v = self.c.filter(empty, u"")
        self.failUnlessEqual(v, u"")
        self.failUnless(isinstance(v, text_type))

    def test_mix_safe(self):
        empty = fsnative(u"")
        safe = u"safe"
        self.failUnlessEqual(self.c.filter(empty, safe), safe)


class TSpacesToUnderscores(TFilter, TFilterMixin):
    Kind = SpacesToUnderscores

    def test_conv(self):
        self.failUnlessEqual(self.c.filter("", "foo bar "), "foo_bar_")


class TStripWindowsIncompat(TFilter, TFilterMixin):
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


class TStripDiacriticals(TFilter, TFilterMixin):
    Kind = StripDiacriticals

    def test_conv(self):
        empty = fsnative(u"")
        test = u"\u00c1 test"
        out = u"A test"
        v = self.c.filter(empty, test)
        self.failUnlessEqual(v, out)
        self.failUnless(isinstance(v, text_type))


class TStripNonASCII(TFilter, TFilterMixin):
    Kind = StripNonASCII

    def test_conv(self):
        empty = fsnative(u"")
        in_ = u"foo \u00c1 \u1234"
        out = u"foo _ _"
        v = self.c.filter(empty, in_)
        self.failUnlessEqual(v, out)
        self.failUnless(isinstance(v, text_type))


class TLowercase(TFilter, TFilterMixin):
    Kind = Lowercase

    def test_conv(self):
        empty = fsnative(u"")

        v = self.c.filter(empty, fsnative(u"foobar baz"))
        self.failUnlessEqual(v, fsnative(u"foobar baz"))
        self.failUnless(isinstance(v, fsnative))

        v = self.c.filter(empty, fsnative(u"Foobar.BAZ"))
        self.failUnlessEqual(v, fsnative(u"foobar.baz"))
        self.failUnless(isinstance(v, fsnative))
