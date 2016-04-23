# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from unittest import TestCase

from quodlibet.query import Query

from quodlibet import const
from quodlibet.util.dprint import print_d

from quodlibet.browsers.soundcloud.util import extract

NONE = set([])


class TestExtract(TestCase):
    def setUpClass(cls):
        const.DEBUG = True

    def tearDownClass(cls):
        const.DEBUG = False

    def test_extract(self):
        self.verify("&(foo, bar)", {"foo", "bar"})
        self.verify("|(either, or)", {"either", "or"})
        self.verify("#(bitrate>128)", NONE)

    def test_extract_inter(self):
        self.verify("genre=&(jazz, funk)", {'jazz', 'funk'})

    def test_extract_union(self):
        self.verify("genre=|(jazz, funk)", {'jazz', 'funk'})

    def test_extract_complex(self):
        self.verify("&(artist='foo', genre=|(rock, metal))",
                    {'foo', 'rock', 'metal'})

    def verify(self, text, expected):
        print_d("Trying '%s'..." % text)
        terms = extract(Query(text)._match)
        print_d("Terms for %s: %r" % (text, terms))
        self.failUnlessEqual(terms, expected)
