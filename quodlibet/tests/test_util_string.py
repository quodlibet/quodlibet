# -*- coding: utf-8 -*-
from tests import TestCase

from quodlibet.util.string.splitters import split_value


class Tsplit_value(TestCase):
    def test_single(self):
        self.failUnlessEqual(split_value("a b"), ["a b"])

    def test_double(self):
        self.failUnlessEqual(split_value("a, b"), ["a", "b"])

    def test_custom_splitter(self):
        self.failUnlessEqual(split_value("a b", [" "]), ["a", "b"])

    def test_two_splitters(self):
        self.failUnlessEqual(
            split_value("a, b and c", [",", "and"]), ["a", "b and c"])

    def test_no_splitters(self):
        self.failUnlessEqual(split_value("a b", []), ["a b"])

    def test_wordboundry(self):
        self.failUnlessEqual(
            split_value("Andromeda and the Band", ["and"]),
            ["Andromeda", "the Band"])

    def test_unicode_wordboundry(self):
        val = '\xe3\x81\x82&\xe3\x81\x84'.decode('utf-8')
        self.failUnlessEqual(split_value(val), val.split("&"))
