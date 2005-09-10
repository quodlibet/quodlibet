from unittest import TestCase
from tests import registerCase

import parser

class ValidityTests(TestCase):
    def test_re(self):
        self.failUnless(parser.is_valid('t = /an re/'))
        self.failUnless(parser.is_valid('t = /an re/c'))
        self.failUnless(parser.is_valid('t = /an\\/re/'))
        self.failIf(parser.is_valid('t = /an/re/'))
    def test_str(self):
        self.failUnless(parser.is_valid('t = "a str"'))
        self.failUnless(parser.is_valid('t = "a str"c'))
        self.failUnless(parser.is_valid('t = "a\\"str"'))
        # there's no equivalent failure for strings since 'str"' would be
        # read as a set of modifiers
    def test_tag(self):
        self.failUnless(parser.is_valid('t = tag'))
        self.failUnless(parser.is_valid('t = !tag'))
        self.failUnless(parser.is_valid('t = |(tag, bar)'))
        self.failUnless(parser.is_valid('t = a"tag"'))
        self.failIf(parser.is_valid('t = a, tag'))

    def test_empty(self):
        self.failUnless(parser.is_valid(''))
        self.failUnless(parser.is_parsable(''))
        self.failUnless(parser.parse(''))

    def test_emptylist(self):
        self.failIf(parser.is_valid("a = &()"))
        self.failIf(parser.is_valid("a = |()"))
        self.failIf(parser.is_valid("|()"))
        self.failIf(parser.is_valid("&()"))

    def test_nonsense(self):
        self.failIf(parser.is_valid('a string'))
        self.failIf(parser.is_valid('t = #(a > b)'))
        self.failIf(parser.is_valid("=a= = /b/"))
        self.failIf(parser.is_valid("a = &(/b//"))
        self.failIf(parser.is_valid("(a = &(/b//)"))

    def test_trailing(self):
        self.failIf(parser.is_valid('t = /an re/)'))
        self.failIf(parser.is_valid('|(a, b = /a/, c, d = /q/) woo'))

    def test_not(self):
        self.failUnless(parser.is_valid('t = !/a/'))
        self.failUnless(parser.is_valid('t = !!/a/'))
        self.failUnless(parser.is_valid('!t = "a"'))
        self.failUnless(parser.is_valid('!!t = "a"'))
        self.failUnless(parser.is_valid('t = !|(/a/, !"b")'))
        self.failUnless(parser.is_valid('t = !!|(/a/, !"b")'))
        self.failUnless(parser.is_valid('!|(t = /a/)'))

    def test_taglist(self):
        self.failUnless(parser.is_valid('a, b = /a/'))
        self.failUnless(parser.is_valid('a, b, c = |(/a/)'))
        self.failUnless(parser.is_valid('|(a, b = /a/, c, d = /q/)'))
        self.failIf(parser.is_valid('a = /a/, b'))

    def test_andor(self):
        self.failUnless(parser.is_valid('a = |(/a/, /b/)'))
        self.failUnless(parser.is_valid('a = |(/b/)'))
        self.failUnless(parser.is_valid('|(a = /b/, c = /d/)'))

        self.failUnless(parser.is_valid('a = &(/a/, /b/)'))
        self.failUnless(parser.is_valid('a = &(/b/)'))
        self.failUnless(parser.is_valid('&(a = /b/, c = /d/)'))
        
    def test_numcmp(self):
        self.failUnless(parser.is_valid("#(t < 3)"))
        self.failUnless(parser.is_valid("#(t <= 3)"))
        self.failUnless(parser.is_valid("#(t > 3)"))
        self.failUnless(parser.is_valid("#(t >= 3)"))
        self.failUnless(parser.is_valid("#(t = 3)"))
        self.failUnless(parser.is_valid("#(t != 3)"))

        self.failIf(parser.is_valid("#(t !> 3)"))
        self.failIf(parser.is_valid("#(t >> 3)"))

    def test_trinary(self):
        self.failUnless(parser.is_valid("#(2 < t < 3)"))
        self.failUnless(parser.is_valid("#(2 >= t > 3)"))
        # useless, but valid
        self.failUnless(parser.is_valid("#(5 > t = 2)"))

    def test_list(self):
        self.failUnless(parser.is_valid("#(t < 3, t > 9)"))
        self.failUnless(parser.is_valid("t = &(/a/, /b/)"))
        self.failUnless(parser.is_valid("s, t = |(/a/, /b/)"))
        self.failUnless(parser.is_valid("|(t = /a/, s = /b/)"))

    def test_nesting(self):
        self.failUnless(parser.is_valid("|(s, t = &(/a/, /b/),!#(2 > q > 3))"))

class ParserTests(TestCase):
    from formats._audio import AudioFile as AF

    def setUp(self):
        self.s1 = self.AF(
            { "album": "I Hate: Tests", "artist": "piman", "title": "Quuxly",
              "version": "cake mix", "~filename": "/dir1/foobar.ogg" })
        self.s2 = self.AF(
            { "album": "Foo the Bar", "artist": "mu", "title": "Rockin' Out",
              "~filename": "/dir2/something.mp3", "tracknumber": "12/15" })

        self.s3 = self.AF({"artist": "piman\nmu"})

    def test_empty(self):
        self.failIf(parser.parse("foobar = /./").search(self.s1))

    def test_re(self):
        for s in ["album = /i hate/", "artist = /pi*/", "title = /x.y/"]:
            self.failUnless(parser.parse(s).search(self.s1))
            self.failIf(parser.parse(s).search(self.s2))
        f = parser.parse("artist = /mu|piman/").search
        self.failUnless(f(self.s1))
        self.failUnless(f(self.s2))

    def test_abbrs(self):
        for s in ["b = /i hate/", "a = /pi*/", "t = /x.y/"]:
            self.failUnless(parser.parse(s).search(self.s1))
            self.failIf(parser.parse(s).search(self.s2))

    def test_str(self):
        for k in self.s2.keys():
            v = self.s2[k]
            self.failUnless(parser.parse('%s = "%s"' % (k, v)).search(self.s2))

    def test_numcmp(self):
        self.failUnless(parser.parse("#(track = 0)").search(self.s1))
        self.failUnless(parser.parse("#(notatag = 0)").search(self.s1))
        self.failUnless(parser.parse("#(track = 12)").search(self.s2))

    def test_trinary(self):
        self.failUnless(parser.parse("#(11 < track < 13)").search(self.s2))
        self.failUnless(parser.parse("#(11 < track <= 12)").search(self.s2))
        self.failUnless(parser.parse("#(12 <= track <= 12)").search(self.s2))
        self.failUnless(parser.parse("#(12 <= track < 13)").search(self.s2))
        self.failUnless(parser.parse("#(13 > track > 11)").search(self.s2))
        self.failUnless(parser.parse("#(20 > track < 20)").search(self.s2))

    def test_not(self):
        for s in ["album = !/i hate/", "artist = !/pi*/", "title = !/x.y/"]:
            self.failUnless(parser.parse(s).search(self.s2))
            self.failIf(parser.parse(s).search(self.s1))

    def test_case(self):
        self.failUnless(parser.parse("album = /i hate/").search(self.s1))
        self.failUnless(parser.parse("album = /I Hate/").search(self.s1))
        self.failUnless(parser.parse("album = /i Hate/").search(self.s1))
        self.failUnless(parser.parse("album = /i Hate/i").search(self.s1))
        self.failIf(parser.parse("album = /i hate/c").search(self.s1))

    def test_re_and(self):
        self.failUnless(parser.parse("album = &(/ate/,/est/)").search(self.s1))
        self.failIf(parser.parse("album = &(/ate/, /ets/)").search(self.s1))
        self.failIf(parser.parse("album = &(/tate/, /ets/)").search(self.s1))

    def test_re_or(self):
        self.failUnless(parser.parse("album = |(/ate/,/est/)").search(self.s1))
        self.failUnless(parser.parse("album = |(/ate/,/ets/)").search(self.s1))
        self.failIf(parser.parse("album = |(/tate/, /ets/)").search(self.s1))

    def test_newlines(self):
        self.failUnless(parser.parse("a = /\n/").search(self.s3))
        self.failUnless(parser.parse("a = /\\n/").search(self.s3))
        self.failIf(parser.parse("a = /\n/").search(self.s2))
        self.failIf(parser.parse("a = /\\n/").search(self.s2))

    def test_exp_and(self):
        self.failUnless(parser.parse(
            "&(album = ate, artist = man)").search(self.s1))
        self.failIf(parser.parse(
            "&(album = ate, artist = nam)").search(self.s1))
        self.failIf(parser.parse(
            "&(album = tea, artist = nam)").search(self.s1))

    def test_exp_or(self):
        self.failUnless(parser.parse(
            "|(album = ate, artist = man)").search(self.s1))
        self.failUnless(parser.parse(
            "|(album = ate, artist = nam)").search(self.s1))
        self.failIf(parser.parse(
            "&(album = tea, artist = nam)").search(self.s1))

    def test_dumb_search(self):
        self.failUnless(parser.parse("ate man").search(self.s1))
        self.failUnless(parser.parse("Ate man").search(self.s1))
        self.failIf(parser.parse("woo man").search(self.s1))
        self.failIf(parser.parse("not crazy").search(self.s1))

    def test_synth_search(self):
        self.failUnless(parser.parse("~dirname=/dir1/").search(self.s1))
        self.failUnless(parser.parse("~dirname=/dir2/").search(self.s2))
        self.failIf(parser.parse("~dirname=/dirty/").search(self.s1))
        self.failIf(parser.parse("~dirname=/dirty/").search(self.s2))

class TestColors(TestCase):
    def test_red(self):
        for p in ["a = /w", "|(sa#"]:
            self.failUnlessEqual("red", parser.is_valid_color(p))

    def test_blue(self):
        for p in ["a test", "more test hooray"]:
            self.failUnlessEqual("blue", parser.is_valid_color(p))

    def test_green(self):
        for p in ["a = /b/", "&(a = b, c = d)"]:
            self.failUnlessEqual("dark green", parser.is_valid_color(p))

registerCase(ValidityTests)
registerCase(ParserTests)
registerCase(TestColors)
