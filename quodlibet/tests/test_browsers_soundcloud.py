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

    @classmethod
    def setUpClass(cls):
        const.DEBUG = True

    @classmethod
    def tearDownClass(cls):
        const.DEBUG = False

    def test_extract_single_tag(self):
        self.verify("artist=jay-z", {"jay-z"})

    def test_extract_unsupported(self):
        self.verify("musicbrainz_discid=12345", NONE)

    def test_extract_composite_text(self):
        self.verify("&(foo, bar)", {"foo", "bar"})
        self.verify("|(either, or)", {"either", "or"})

    def test_numeric_simple(self):
        self.verify("#(length=180)", {180}, term='length')

    def test_extract_date(self):
        self.verify("#(date>today)", {180}, term='length')

    def test_numeric_relative(self):
        self.verify("#(length>180)", {180}, term='length[from]')
        self.verify("#(180<=length)", {180}, term='length[from]')
        self.verify("#(length<360)", {360}, term='length[to]')
        self.verify("#(360>=length)", {360}, term='length[to]')

    def test_extract_tag_inter(self):
        self.verify("genre=&(jazz, funk)", {'jazz', 'funk'})

    def test_extract_tag_union(self):
        self.verify("genre=|(jazz, funk)", {'jazz', 'funk'})

    def test_extract_complex(self):
        self.verify("&(artist='foo', genre=|(rock, metal))",
                    {'foo', 'rock', 'metal'})

    def verify(self, text, expected, term='q'):
        print_d("Trying '%s'..." % text)
        terms = extract(Query(text)._match)
        self.failUnlessEqual(terms[term], expected,
                             msg="terms[%s] wasn't %r. Full terms: %r"
                                 % (term, expected, terms))
