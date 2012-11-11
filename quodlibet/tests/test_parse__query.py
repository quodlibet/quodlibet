# -*- encoding: utf-8 -*-
from tests import TestCase, add

from quodlibet.parse import Query

class TQuery_is_valid(TestCase):
    def test_re(self):
        self.failUnless(Query.is_valid('t = /an re/'))
        self.failUnless(Query.is_valid('t = /an re/c'))
        self.failUnless(Query.is_valid('t = /an\\/re/'))
        self.failIf(Query.is_valid('t = /an/re/'))
        self.failUnless(Query.is_valid('t = /aaa/lsic'))
        self.failIf(Query.is_valid('t = /aaa/icslx'))
    def test_str(self):
        self.failUnless(Query.is_valid('t = "a str"'))
        self.failUnless(Query.is_valid('t = "a str"c'))
        self.failUnless(Query.is_valid('t = "a\\"str"'))
        # there's no equivalent failure for strings since 'str"' would be
        # read as a set of modifiers
    def test_tag(self):
        self.failUnless(Query.is_valid('t = tag'))
        self.failUnless(Query.is_valid('t = !tag'))
        self.failUnless(Query.is_valid('t = |(tag, bar)'))
        self.failUnless(Query.is_valid('t = a"tag"'))
        self.failIf(Query.is_valid('t = a, tag'))

    def test_empty(self):
        self.failUnless(Query.is_valid(''))
        self.failUnless(Query.is_parsable(''))
        self.failUnless(Query(''))

    def test_emptylist(self):
        self.failIf(Query.is_valid("a = &()"))
        self.failIf(Query.is_valid("a = |()"))
        self.failIf(Query.is_valid("|()"))
        self.failIf(Query.is_valid("&()"))

    def test_nonsense(self):
        self.failIf(Query.is_valid('a string'))
        self.failIf(Query.is_valid('t = #(a > b)'))
        self.failIf(Query.is_valid("=a= = /b/"))
        self.failIf(Query.is_valid("a = &(/b//"))
        self.failIf(Query.is_valid("(a = &(/b//)"))

    def test_trailing(self):
        self.failIf(Query.is_valid('t = /an re/)'))
        self.failIf(Query.is_valid('|(a, b = /a/, c, d = /q/) woo'))

    def test_not(self):
        self.failUnless(Query.is_valid('t = !/a/'))
        self.failUnless(Query.is_valid('t = !!/a/'))
        self.failUnless(Query.is_valid('!t = "a"'))
        self.failUnless(Query.is_valid('!!t = "a"'))
        self.failUnless(Query.is_valid('t = !|(/a/, !"b")'))
        self.failUnless(Query.is_valid('t = !!|(/a/, !"b")'))
        self.failUnless(Query.is_valid('!|(t = /a/)'))

    def test_taglist(self):
        self.failUnless(Query.is_valid('a, b = /a/'))
        self.failUnless(Query.is_valid('a, b, c = |(/a/)'))
        self.failUnless(Query.is_valid('|(a, b = /a/, c, d = /q/)'))
        self.failIf(Query.is_valid('a = /a/, b'))

    def test_andor(self):
        self.failUnless(Query.is_valid('a = |(/a/, /b/)'))
        self.failUnless(Query.is_valid('a = |(/b/)'))
        self.failUnless(Query.is_valid('|(a = /b/, c = /d/)'))

        self.failUnless(Query.is_valid('a = &(/a/, /b/)'))
        self.failUnless(Query.is_valid('a = &(/b/)'))
        self.failUnless(Query.is_valid('&(a = /b/, c = /d/)'))

    def test_numcmp(self):
        self.failUnless(Query.is_valid("#(t < 3)"))
        self.failUnless(Query.is_valid("#(t <= 3)"))
        self.failUnless(Query.is_valid("#(t > 3)"))
        self.failUnless(Query.is_valid("#(t >= 3)"))
        self.failUnless(Query.is_valid("#(t = 3)"))
        self.failUnless(Query.is_valid("#(t != 3)"))

        self.failIf(Query.is_valid("#(t !> 3)"))
        self.failIf(Query.is_valid("#(t >> 3)"))

    def test_trinary(self):
        self.failUnless(Query.is_valid("#(2 < t < 3)"))
        self.failUnless(Query.is_valid("#(2 >= t > 3)"))
        # useless, but valid
        self.failUnless(Query.is_valid("#(5 > t = 2)"))

    def test_list(self):
        self.failUnless(Query.is_valid("#(t < 3, t > 9)"))
        self.failUnless(Query.is_valid("t = &(/a/, /b/)"))
        self.failUnless(Query.is_valid("s, t = |(/a/, /b/)"))
        self.failUnless(Query.is_valid("|(t = /a/, s = /b/)"))

    def test_nesting(self):
        self.failUnless(Query.is_valid("|(s, t = &(/a/, /b/),!#(2 > q > 3))"))
add(TQuery_is_valid)

class TQuery(TestCase):
    from quodlibet.formats._audio import AudioFile as AF

    def setUp(self):
        self.s1 = self.AF(
            { "album": "I Hate: Tests", "artist": "piman", "title": "Quuxly",
              "version": "cake mix", "~filename": "/dir1/foobar.ogg" })
        self.s2 = self.AF(
            { "album": "Foo the Bar", "artist": "mu", "title": "Rockin' Out",
              "~filename": "/dir2/something.mp3", "tracknumber": "12/15" })

        self.s3 = self.AF(
            {"artist": "piman\nmu",
             "~filename": "/test/\xc3\xb6\xc3\xa4\xc3\xbc/fo\xc3\xbc.ogg"})
        self.s4 = self.AF({"title": u"Ångström", })
        self.s5 = self.AF({"title": "oh&blahhh", "artist": "!ohno"})

    def test_2007_07_27_synth_search(self):
        song = self.AF({"~filename": "foo/64K/bar.ogg"})
        query = Query("~dirname = !64K")
        self.failIf(query.search(song), "%r, %r" % (query, song))

    def test_empty(self):
        self.failIf(Query("foobar = /./").search(self.s1))

    def test_gte(self):
        self.failUnless(Query("#(track >= 11)").search(self.s2))

    def test_re(self):
        for s in ["album = /i hate/", "artist = /pi*/", "title = /x.y/"]:
            self.failUnless(Query(s).search(self.s1))
            self.failIf(Query(s).search(self.s2))
        f = Query("artist = /mu|piman/").search
        self.failUnless(f(self.s1))
        self.failUnless(f(self.s2))

    def test_not(self):
        for s in ["album = !hate", "artist = !pi"]:
            self.failIf(Query(s).search(self.s1))
            self.failUnless(Query(s).search(self.s2))

    def test_abbrs(self):
        for s in ["b = /i hate/", "a = /pi*/", "t = /x.y/"]:
            self.failUnless(Query(s).search(self.s1))
            self.failIf(Query(s).search(self.s2))

    def test_str(self):
        for k in self.s2.keys():
            v = self.s2[k]
            self.failUnless(Query('%s = "%s"' % (k, v)).search(self.s2))
            self.failIf(Query('%s = !"%s"' % (k, v)).search(self.s2))

    def test_numcmp(self):
        self.failIf(Query("#(track = 0)").search(self.s1))
        self.failIf(Query("#(notatag = 0)").search(self.s1))
        self.failUnless(Query("#(track = 12)").search(self.s2))

    def test_trinary(self):
        self.failUnless(Query("#(11 < track < 13)").search(self.s2))
        self.failUnless(Query("#(11 < track <= 12)").search(self.s2))
        self.failUnless(Query("#(12 <= track <= 12)").search(self.s2))
        self.failUnless(Query("#(12 <= track < 13)").search(self.s2))
        self.failUnless(Query("#(13 > track > 11)").search(self.s2))
        self.failUnless(Query("#(20 > track < 20)").search(self.s2))

    def test_not_2(self):
        for s in ["album = !/i hate/", "artist = !/pi*/", "title = !/x.y/"]:
            self.failUnless(Query(s).search(self.s2))
            self.failIf(Query(s).search(self.s1))

    def test_case(self):
        self.failUnless(Query("album = /i hate/").search(self.s1))
        self.failUnless(Query("album = /I Hate/").search(self.s1))
        self.failUnless(Query("album = /i Hate/").search(self.s1))
        self.failUnless(Query("album = /i Hate/i").search(self.s1))
        self.failUnless(Query(u"title = /ångström/").search(self.s4))
        self.failIf(Query("album = /i hate/c").search(self.s1))
        self.failIf(Query(u"title = /ångström/c").search(self.s4))

    def test_re_and(self):
        self.failUnless(Query("album = &(/ate/,/est/)").search(self.s1))
        self.failIf(Query("album = &(/ate/, /ets/)").search(self.s1))
        self.failIf(Query("album = &(/tate/, /ets/)").search(self.s1))

    def test_re_or(self):
        self.failUnless(Query("album = |(/ate/,/est/)").search(self.s1))
        self.failUnless(Query("album = |(/ate/,/ets/)").search(self.s1))
        self.failIf(Query("album = |(/tate/, /ets/)").search(self.s1))

    def test_newlines(self):
        self.failUnless(Query("a = /\n/").search(self.s3))
        self.failUnless(Query("a = /\\n/").search(self.s3))
        self.failIf(Query("a = /\n/").search(self.s2))
        self.failIf(Query("a = /\\n/").search(self.s2))

    def test_exp_and(self):
        self.failUnless(Query("&(album = ate, artist = man)").search(self.s1))
        self.failIf(Query("&(album = ate, artist = nam)").search(self.s1))
        self.failIf(Query("&(album = tea, artist = nam)").search(self.s1))

    def test_exp_or(self):
        self.failUnless(Query("|(album = ate, artist = man)").search(self.s1))
        self.failUnless(Query("|(album = ate, artist = nam)").search(self.s1))
        self.failIf(Query("&(album = tea, artist = nam)").search(self.s1))

    def test_dumb_search(self):
        self.failUnless(Query("ate man").search(self.s1))
        self.failUnless(Query("Ate man").search(self.s1))
        self.failIf(Query("woo man").search(self.s1))
        self.failIf(Query("not crazy").search(self.s1))

    def test_dumb_search_value(self):
        self.failUnless(Query("|(ate, foobar)").search(self.s1))
        self.failUnless(Query("!!|(ate, foobar)").search(self.s1))
        self.failUnless(Query("&(ate, te)").search(self.s1))
        self.failIf(Query("|(foo, bar)").search(self.s1))
        self.failIf(Query("&(ate, foobar)").search(self.s1))
        self.failIf(Query("! !&(ate, foobar)").search(self.s1))
        self.failIf(Query("&blah").search(self.s1))
        self.failUnless(Query("&blah oh").search(self.s5))
        self.failUnless(Query("!oh no").search(self.s5))
        self.failIf(Query("|blah").search(self.s1))
        # http://code.google.com/p/quodlibet/issues/detail?id=1056
        self.failUnless(Query("&(ate, piman)").search(self.s1))

    def test_dumb_search_value_negate(self):
        self.failUnless(Query("!xyz").search(self.s1))
        self.failUnless(Query("!!!xyz").search(self.s1))
        self.failUnless(Query(" !!!&(xyz, zyx)").search(self.s1))
        self.failIf(Query("!man").search(self.s1))

    def test_dumb_search_regexp(self):
        self.failUnless(Query("/(x|H)ate/").search(self.s1))
        self.failUnless(Query("'PiMan'").search(self.s1))
        self.failIf(Query("'PiMan'c").search(self.s1))
        self.failUnless(Query("!'PiMan'c").search(self.s1))
        self.failIf(Query("!/(x|H)ate/").search(self.s1))

    def test_unslashed_search(self):
        self.failUnless(Query("artist=piman").search(self.s1))
        self.failUnless(Query(u"title=ång").search(self.s4))
        self.failIf(Query("artist=mu").search(self.s1))
        self.failIf(Query(u"title=äng").search(self.s4))

    def test_synth_search(self):
        self.failUnless(Query("~dirname=/dir1/").search(self.s1))
        self.failUnless(Query("~dirname=/dir2/").search(self.s2))
        self.failIf(Query("~dirname=/dirty/").search(self.s1))
        self.failIf(Query("~dirname=/dirty/").search(self.s2))

    def test_search_almostequal(self):
        a, b = self.AF({"~#rating": 0.771}), self.AF({"~#rating": 0.769})
        self.failUnless(Query("#(rating = 0.77)").search(a))
        self.failUnless(Query("#(rating = 0.77)").search(b))

    def test_and_or_operator(self):
        union = Query("|(foo=bar,bar=foo)")
        inter = Query("&(foo=bar,bar=foo)")
        neg = Query("foo=!bar")
        numcmp = Query("#(bar = 0)")
        tag = Query("foo=bar")

        tests = [inter | tag, tag | tag, neg | neg, tag | inter, neg | union,
            union | union, inter | inter, numcmp | numcmp, numcmp | union]

        self.failIf(filter(lambda x: not isinstance(x, type(union)), tests))

        tests = [inter & tag, tag & tag, neg & neg, tag & inter, neg & union,
            union & union, inter & inter, numcmp & numcmp, numcmp & inter]

        self.failIf(filter(lambda x: not isinstance(x, type(inter)), tests))

    def test_match_all(self):
        self.failUnless(Query.match_all(""))
        self.failUnless(Query.match_all("    "))
        self.failIf(Query.match_all("foo"))

    def test_fs_utf8(self):
        self.failUnless(Query(u"~filename=foü.ogg").search(self.s3))
        self.failUnless(Query(u"~filename=öä").search(self.s3))
        self.failUnless(Query(u"~dirname=öäü").search(self.s3))
        self.failUnless(Query(u"~basename=ü.ogg").search(self.s3))

add(TQuery)

class TQuery_is_valid_color(TestCase):
    def test_red(self):
        for p in ["a = /w", "|(sa#"]:
            self.failUnlessEqual(False, Query.is_valid_color(p))

    def test_black(self):
        for p in ["a test", "more test hooray"]:
            self.failUnlessEqual(None, Query.is_valid_color(p))

    def test_green(self):
        for p in ["a = /b/", "&(a = b, c = d)", "/abc/", "!x", "!&(abc, def)"]:
            self.failUnlessEqual(True, Query.is_valid_color(p))
add(TQuery_is_valid_color)
