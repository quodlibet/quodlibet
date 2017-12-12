# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import print_d
from quodlibet.query import QueryType
from tests import TestCase
from quodlibet.query.mql import Mql, ParseError
import quodlibet.formats._audio as audio


def AF(*args, **kwargs):
    a = audio.AudioFile(*args, **kwargs)
    return a


class TMQL(TestCase):
    def _check_parsing(self, data):
        for expr, expected in data:
            query = Mql(expr)
            self.failUnlessEqual(expected, query.type == QueryType.VALID,
                                 msg="{%s} should have failed but came back %r"
                                     % (expr, query))

    def _check_matching(self, tests, song):

        for expr, expected in tests:
            print_d("*** Trying: {%s} ***" % expr)
            try:
                m = Mql(expr,
                        star=["artist", "title", "version", "album",
                              "genre", "comment", "~dirname", "genre",
                              "performer", "originalartist"])
                print_d("Reformatted={%s}" % m.pp_query.transformString(expr))
            except ParseError as pe:
                self.fail("{%s} died unexpectedly (%s)" % (expr, pe))
            else:
                self.assertEquals(expected, m.search(song),
                                  "{%s} should %shave matched song: %s"
                                  % (expr, ["not ", ""][expected], song))

    # ***********************************************************************
    def test_basic_parsing(self):
        __DATA = [
            ("foo", True),
            ("foo???43g", True),
            ("=", False),
            ("foo man", True),
            (u"œufs", True),
            (u"l'élève franćais qui aime le goût d'œufs à Noël", True),
            ("(foo)", True),
            ("album=", False),
            ("~dirname", False),
            ("/a/b/c", False),  # Better disallowed (regex)
            ("~dirname=foo", True),
            ("'jeepers'", True),
            ("\"ouch", False),
            ("didn't think o' that", True),
            ("artist=value and", False),
            ("bill ANDY ted", True),
            ("/foo/", True),
            ("/([a-c!\"#_]{1,3}foo)/", True),
            ("Bill AND \"Ted\"", True),
            ("title in [Baz,random]", True),
            ("foo LIMIT", False)]
        self._check_parsing(__DATA)

    def test_parsing_unknown_tags(self):
        self._check_parsing([
            ("artXXX=\"foo\"", False),
            ("artistic=\"foo\"", False),
            ("~artistic=\"foo\"", True)])

    def test_basic_numeric_parsing(self):
        self._check_parsing([
            ("~#length=foo", False),
            ("~#length=123", True),
            ("~#rating=0.5", True),
            # Anything is ok if using ~#
            ("~#foobar=0.5", True)
        ])

    def test_limits_parsing(self):
        __DATA = [
            ("LIMIT 123", True),
            ("foo LIMIT 10", True),
            ("foo LIMIT -10", False),
            ("foo LIMIT 10 MB", True),
            ("foo LIMIT badword", False),
            ("foo LIMIT 10 SONGS", True),
        ]
        self._check_parsing(__DATA)

    song1 = AF({
        "album": "I Hate tests", "artist": "foo", "title": "bar",
        "version": "cake-mix", "genre": "Jazz",
        "originalartist": 'AC/DC',
        "comment": u"œufs à Noël",
        "~filename": u"/dir1/œufs.ogg",
        "~#length": 120, "~#filesize": 12345})
    song2 = AF({
        "album": "Foo the Bar", "artist": "mu\nAdditional Dude",
        "title": "Baz Rockin' Out", "performer": u"Dr. Dre\nœufs",
        "version": "ca$h/m0ney rem1x!",
        "~filename": "/dir2/subdir/something.mp3",
        "tracknumber": "12/15",
        "~#length": 99,
        "~#filesize": 999999,
        "~replaygain_track_gain": "-2.3 dB",
        "genre": "Blues Rock\nPop"})

    def test_simple(self):
        __DATA = [
            ("BilllyBobFooMAn", False),
            ("I Hate tests", True),
            ("cake-mix", True),
            ("\"I Hate tests\"", True),
            ("'I Hate tests'", True),
            ("'I Hate tests' foo", True),
            ("\"I might Hate tests\"", False),
            ("ridiculous set of unimaginable conditions", False),
        ]
        self._check_matching(__DATA, self.song1)

    def test_empty(self):
        self._check_matching([("originalartist=''", False)], self.song1)
        self._check_matching([("originalartist=''", True)], self.song2)

    def test_partial_matching(self):
        __DATA = [
            ("'Hate tests'", False),
            ("'I Hate tests'", True),
            ("'I Hate tes'", False),
            ("'I Hate tests' foo", True),
            ("ight Hat", False),
            ("set of un", False),
            ("Cow Rockin'", False),
            ('"set of un"', False),
        ]
        self._check_matching(__DATA, self.song1)

    def test_equality(self):
        __DATA = [
            ("artist=value", False),
            ("artist=\"oo\"", False),
            ("title = \"bar\"", True),
            ("title = \"ba\"", False),
            ("artist!=value", True),
            ("artist!=foo", False),
            ("artist=foo", True),
            ("album=Hate", True),
            ("artist=\"Brandy & Monica\"", False),
            ("title = \"test\"", False),
            ("version=cake-mix", True),
            ("originalartist='AC/DC'", True),
        ]
        self._check_matching(__DATA, self.song1)

    def test_negated_tags(self):
        self._check_matching([
                                 ("!artist", False),
                                 ("!albumartist", True),
                                 ("!~albumartist", True),
                                 ("!performer", True)], self.song1)

    # def test_excluded_equality(self):
    # __DATA = [
    #         ("artist='value' BUT NOT other",    False),
    #         ("artist=other BUT NOT value",    False),
    #         ("title = \"Hate\" BUT NOT tests", False),
    #         ("title = \"Hate\" BUT NOT random", True),
    #         ("artist=foo BUT NOT foo", False),
    #     ]
    #     self._check_matching(__DATA, self.song1)

    def test_internal_tags(self):
        __DATA = [
            # FIXME: Why does this break in the tests, but not in QL???
            # ("~dirname='/dir1'",    True),
            ("~dirname=dir1", True),
            ("~dirname='/tmp'", False),
            ("~#length=120", True),
            ("~#length != 120", False),
            ("~#length < 3200", True),
            ("~#length > 3200", False),
            ("~#filesize < 1000", False),
        ]
        self._check_matching(__DATA, self.song1)

    def test_special(self):
        __DATA = [
            ("money e^^ek ", False),
            ("Dr. Dre ", True),
            ("Dr? Dre ", False),
            ("ca$h m0ney", True),
        ]
        self._check_matching(__DATA, self.song2)

    def test_multiple(self):
        __DATA = [
            ("artist=additional", True),
            ("performer=Dre", True),
            ("performer = \"Mrs Dre\"", False),
            ("performer = \"Dr. Dre\"", True),
            ("genre = \"Pop\"", True),
            ("genre = Blues", True),
            ("genre = Rock", True),
            ("genre = \"Metal\"", False),
        ]
        self._check_matching(__DATA, self.song2)

    def test_junctions(self):
        __DATA = [
            ("artist=foo AND album=fuzz", False),
            ("foo AND bar", True),
            ("foo ANDY bar", False),
            ('Bill and Ted', False),
            ('Bill AND "Ted"', False),
            ('"Bill" AND "Ted"', False),
            ("artist=foo AND album=\"I Hate tests\"", True),
            ("artist=\"foo\" OR album = \"Best Of\"", True),
            ("title=bar or album = bar OR album=baz", True),
            ("title=foobar AND (album = Bar OR album=baz)", False),
            ("title=ba AND (album=testz OR "
             "(artist=oo and (version=cake or spaceman)))", True),
        ]
        self._check_matching(__DATA, self.song1)

    def test_bare_regex(self):
        __DATA = [
            ("/foo/ AND /bar/", True),
            ('/Bill/ AND /Ted/', False),
            ("/cake-mix/", True),
            ("/foop/", False),
            ("/^Hate/", False),
            ("/^I Hate/", True),
            (u"/œufs/", True),

        ]
        self._check_matching(__DATA, self.song1)

    def test_regex_expr(self):
        __DATA = [
            ("artist=/foo/", True),
            ("artist=/foop/", False),
            ("artist=/f[o]{3,3}/", False),
            ("artist=/f[o]{1,3}/", True),
            ("artist=foo AND album=/Hat.? t[es]*ts?/", True),
            ("album=/[0-9]+/", False),
            ("album=/Hate/", True),
            ("album=/^Hate/", False),
            ("album=/^Hate/ OR album=/Hate$/", False),
            ("album=/^I Hate/", True),
            ("album=/^I Hate/ AND album=/Hate Tests/", True),
            ("album = /^I Hate/ AND artist=food", False),
            ("album != /^I Hate/", False),

            ("album = /Hate Tests$/", True),
            ("album = /[a-zA-Z\ ]+/", True),
            (u"comment = /œufs/", True),
        ]
        self._check_matching(__DATA, self.song1)

    def test_in_clause(self):
        __DATA = [
            ("artist in [mu]", True),
            ("genre in [blues]", True),
            ("title in [baz,random]", True),
            ("title in [unlikely]", False),
            ("title in [baz]", True),
            ("title in [\"Baz Rockin' Out\"]", True),
            ("title in [very, unlikely]", False),
            ("title in []", False),
            ("title in [\"Baz Rockin' Out\"] AND randomvalue", False),
            ("title in [Baz, \"baa\"] AND Bar", True),
            ("title in [the] AND artist IN [mu]", False),
            ("title in [Baz] AND artist IN [\"mu\"]", True),
        ]
        self._check_matching(__DATA, self.song2)

    def test_limit_clause(self):
        __DATA = [
            ("foo LIMIT 1", True),
            ('genre = "Jazz" LIMIT 124689', True),
            ("artist=foo LIMIT 3 HOURS", True),
            ("album=tests LIMIT 1 Mins", True),
            ("album=tests LIMIT 3 Mins", True),
            ("foo LIMIT 1 HOUR", True),
            ("foo LIMIT 112345 HR", True),
            ("\"I hate tests\" LIMIT 1MB", True),
            ("foo bar LIMIT 10 GB", True),
        ]
        self._check_matching(__DATA, self.song1)

    def test_limit_tag_clause(self):
        __DATA = [
            ("foo LIMIT 3 songs", True),
            ('genre = "Jazz" LIMIT 1 ARTIST', True),
            ('genre = "Jazz" LIMIT 0 artists', True),
            ("album=tests LIMIT 1 Mins", True),
        ]
        self._check_matching(__DATA, self.song1)
