from tests import TestCase

import os

from quodlibet.qltk.tagsfrompath import TagsFromPattern
from quodlibet.qltk.tagsfrompath import (TitleCase, SplitTag,
    UnderscoresToSpaces)
import quodlibet.config


class FilterTestCase(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.c = self.Kind()

    def tearDown(self):
        self.c.destroy()
        quodlibet.config.quit()


class TTitleCase(FilterTestCase):
    Kind = TitleCase

    def test_simple(self):
        self.failUnlessEqual(self.c.filter("title", "foo bar"), "Foo Bar")

    def test_apostrophe(self):
        self.failUnlessEqual(self.c.filter("title", "IT's"), "IT's")


class TSplitTag(FilterTestCase):
    Kind = SplitTag

    def test_simple(self):
        self.failUnlessEqual(self.c.filter("title", "foo & bar"), "foo\nbar")


class TUnderscoresToSpaces(FilterTestCase):
    Kind = UnderscoresToSpaces

    def test_simple(self):
        self.failUnlessEqual(self.c.filter("titke", "foo_bar"), "foo bar")
