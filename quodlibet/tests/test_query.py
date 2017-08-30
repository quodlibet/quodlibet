# -*- encoding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
import time

from senf import fsnative

from quodlibet import config
from quodlibet.compat import xrange
from quodlibet.formats import AudioFile
from quodlibet.query import Query, QueryType
from quodlibet.query import _match as match
from tests import TestCase, skip


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
        self.failUnless(Query.is_valid('tag with spaces = tag'))

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

    def test_numcmp_func(self):
        self.assertTrue(Query.is_valid("#(t:min < 3)"))
        self.assertTrue(
            Query.is_valid("&(#(playcount:min = 0), #(added < 1 month ago))"))

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

    def test_extension(self):
        self.failUnless(Query.is_valid("@(name)"))
        self.failUnless(Query.is_valid("@(name: extension body)"))
        self.failUnless(Query.is_valid("@(name: body (with (nested) parens))"))
        self.failUnless(Query.is_valid(r"@(name: body \\ with \) escapes)"))

        self.failIf(Query.is_valid("@()"))
        self.failIf(Query.is_valid(r"@(invalid %name!\\)"))
        self.failIf(Query.is_valid("@(name: mismatched ( parenthesis)"))
        self.failIf(Query.is_valid(r"@(\()"))
        self.failIf(Query.is_valid("@(name:unclosed body"))
        self.failIf(Query.is_valid("@ )"))

    def test_numexpr(self):
        self.failUnless(Query.is_valid("#(t < 3*4)"))
        self.failUnless(Query.is_valid("#(t * (1+r) < 7)"))
        self.failUnless(Query.is_valid("#(0 = t)"))
        self.failUnless(Query.is_valid("#(t < r < 9)"))
        self.failUnless(Query.is_valid("#((t-9)*r < -(6*2) = g*g-1)"))
        self.failUnless(Query.is_valid("#(t + 1 + 2 + -4 * 9 > g*(r/4 + 6))"))
        self.failUnless(Query.is_valid("#(date < 2010-4)"))
        self.failUnless(Query.is_valid("#(date < 2010 - 4)"))
        self.failUnless(Query.is_valid("#(date > 0000)"))
        self.failUnless(Query.is_valid("#(date > 00004)"))
        self.failUnless(Query.is_valid("#(t > 3 minutes)"))
        self.failUnless(Query.is_valid("#(added > today)"))
        self.failUnless(Query.is_valid("#(length < 5:00)"))
        self.failUnless(Query.is_valid("#(filesize > 5M)"))
        self.failUnless(Query.is_valid("#(added < 7 days ago)"))

        self.failIf(Query.is_valid("#(3*4)"))
        self.failIf(Query.is_valid("#(t = 3 + )"))
        self.failIf(Query.is_valid("#(t = -)"))
        self.failIf(Query.is_valid("#(-4 <)"))
        self.failIf(Query.is_valid("#(t < ()"))
        self.failIf(Query.is_valid("#((t +) - 1 > 8)"))
        self.failIf(Query.is_valid("#(t += 8)"))


class TQuery(TestCase):

    def setUp(self):
        config.init()
        self.s1 = AudioFile(
            {"album": u"I Hate: Tests", "artist": u"piman", "title": u"Quuxly",
             "version": u"cake mix",
             "~filename": fsnative(u"/dir1/foobar.ogg"),
             "~#length": 224, "~#skipcount": 13, "~#playcount": 24,
             "date": u"2007-05-24"})
        self.s2 = AudioFile(
            {"album": u"Foo the Bar", "artist": u"mu", "title": u"Rockin' Out",
             "~filename": fsnative(u"/dir2/something.mp3"),
             "tracknumber": u"12/15"})

        self.s3 = AudioFile({
            "artist": u"piman\nmu",
            "~filename": fsnative(u"/test/\xf6\xe4\xfc/fo\xfc.ogg"),
            "~mountpoint": fsnative(u"/bla/\xf6\xe4\xfc/fo\xfc"),
        })
        self.s4 = AudioFile({"title": u"Ångström", "utf8": u"Ångström"})
        self.s5 = AudioFile({"title": u"oh&blahhh", "artist": u"!ohno"})

    def tearDown(self):
        config.quit()

    def test_basic_tag(self):
        assert Query("album=foo").search(self.s2)
        assert not Query("album=.").search(self.s2)
        assert Query("album=/./").search(self.s2)

    def test_inequality(self):
        self.failUnless(Query("album!=foo").search(self.s1))
        self.failIf(Query("album!=foo").search(self.s2))

    @skip("Enable for basic benchmarking of Query")
    def test_inequality_performance(self):
        t = time.time()
        for i in xrange(500):
            # Native assert is a bit lighter...
            assert Query("album!=foo the bar").search(self.s1)
            assert Query("album=foo the bar").search(self.s2)
            assert Query("foo the bar").search(self.s2)
            assert not Query("foo the bar").search(self.s1)
        us = (time.time() - t) * 1000000 / ((i + 1) * 4)
        print("Blended Query searches average %.0f μs" % us)

    @skip("Enable for basic benchmarking of Query")
    def test_inequality_equalish_performance(self):
        t0 = time.time()
        repeats = 2000
        for i in xrange(repeats):
            assert Query("album!=foo the bar").search(self.s1)
        ineq_time = (time.time() - t0)
        t1 = time.time()
        for i in xrange(repeats):
            assert Query("album=!foo the bar").search(self.s1)
        not_val_time = (time.time() - t1)
        self.assertAlmostEqual(ineq_time, not_val_time, places=1)

    def test_repr(self):
        query = Query("foo = bar", [])
        self.assertEqual(
            repr(query).replace("u'", "'"),
            "<Query string='foo = bar' type=QueryType.VALID star=[]>")

        query = Query("bar", ["foo"])
        self.assertEqual(
            repr(query).replace("u'", "'"),
            "<Query string='&(/bar/d)' type=QueryType.TEXT star=['foo']>")

    def test_2007_07_27_synth_search(self):
        song = AudioFile({"~filename": fsnative(u"foo/64K/bar.ogg")})
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

    def test_re_escape(self):
        af = AudioFile({"foo": "\""})
        assert Query('foo="\\""').search(af)
        af = AudioFile({"foo": "/"})
        assert Query('foo=/\\//').search(af)

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
        # https://github.com/quodlibet/quodlibet/issues/1056
        self.failUnless(Query("&(ate, piman)").search(self.s1))

    def test_dumb_search_value_negate(self):
        self.failUnless(Query("!xyz").search(self.s1))
        self.failUnless(Query("!!!xyz").search(self.s1))
        self.failUnless(Query(" !!!&(xyz, zyx)").search(self.s1))
        self.failIf(Query("!man").search(self.s1))

        self.failUnless(Query("&(tests,piman)").search(self.s1))
        self.failUnless(Query("&(tests,!nope)").search(self.s1))
        self.failIf(Query("&(tests,!!nope)").search(self.s1))
        self.failIf(Query("&(tests,!piman)").search(self.s1))
        self.failUnless(Query("&(tests,|(foo,&(pi,!nope)))").search(self.s1))

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
        a, b = AudioFile({"~#rating": 0.771}), AudioFile({"~#rating": 0.769})
        self.failUnless(Query("#(rating = 0.77)").search(a))
        self.failUnless(Query("#(rating = 0.77)").search(b))

    def test_and_or_neg_operator(self):
        union = Query("|(foo=bar,bar=foo)")
        inter = Query("&(foo=bar,bar=foo)")
        neg = Query("!foo=bar")
        numcmp = Query("#(bar = 0)")
        tag = Query("foo=bar")

        tests = [inter | tag, tag | tag, neg | neg, tag | inter, neg | union,
            union | union, inter | inter, numcmp | numcmp, numcmp | union]

        self.failIf(
            list(filter(lambda x: not isinstance(x, match.Union), tests)))

        tests = [inter & tag, tag & tag, neg & neg, tag & inter, neg & union,
            union & union, inter & inter, numcmp & numcmp, numcmp & inter]

        self.failIf(
            list(filter(lambda x: not isinstance(x, match.Inter), tests)))

        self.assertTrue(isinstance(-neg, match.Tag))

        true = Query("")
        self.assertTrue(isinstance(true | inter, match.True_))
        self.assertTrue(isinstance(inter | true, match.True_))
        self.assertTrue(isinstance(true & inter, match.Inter))
        self.assertTrue(isinstance(inter & true, match.Inter))
        self.assertTrue(isinstance(true & true, match.True_))
        self.assertTrue(isinstance(true | true, match.True_))
        self.assertTrue(isinstance(-true, match.Neg))

    def test_filter(self):
        q = Query("artist=piman")
        self.assertEqual(q.filter([self.s1, self.s2]), [self.s1])
        self.assertEqual(q.filter(iter([self.s1, self.s2])), [self.s1])

        q = Query("")
        self.assertEqual(q.filter([self.s1, self.s2]), [self.s1, self.s2])
        self.assertEqual(
            q.filter(iter([self.s1, self.s2])), [self.s1, self.s2])

    def test_match_all(self):
        self.failUnless(Query.match_all(""))
        self.failUnless(Query.match_all("    "))
        self.failIf(Query.match_all("foo"))

    def test_utf8(self):
        # also handle undecoded values
        self.assertTrue(Query(u"utf8=Ångström").search(self.s4))

    def test_fs_utf8(self):
        self.failUnless(Query(u"~filename=foü.ogg").search(self.s3))
        self.failUnless(Query(u"~filename=öä").search(self.s3))
        self.failUnless(Query(u"~dirname=öäü").search(self.s3))
        self.failUnless(Query(u"~basename=ü.ogg").search(self.s3))

    def test_filename_utf8_fallback(self):
        self.failUnless(Query(u"filename=foü.ogg").search(self.s3))
        self.failUnless(Query(u"filename=öä").search(self.s3))

    def test_mountpoint_utf8_fallback(self):
        self.failUnless(Query(u"mountpoint=foü").search(self.s3))
        self.failUnless(Query(u"mountpoint=öä").search(self.s3))

    def test_mountpoint_no_value(self):
        af = AudioFile({"~filename": fsnative(u"foo")})
        assert not Query(u"~mountpoint=bla").search(af)

    def test_star_numeric(self):
        self.assertRaises(ValueError, Query, u"foobar", star=["~#mtime"])

    def test_match_diacriticals_explcit(self):
        assert Query(u'title=angstrom').search(self.s4)
        self.failIf(Query(u'title="Ångstrom"').search(self.s4))
        self.failUnless(Query(u'title="Ångstrom"d').search(self.s4))
        self.failUnless(Query(u'title=Ångström').search(self.s4))
        self.failUnless(Query(u'title="Ångström"').search(self.s4))
        self.failUnless(Query(u'title=/Ångström/').search(self.s4))
        self.failUnless(Query(u'title="Ångstrom"d').search(self.s4))
        self.failUnless(Query(u'title=/Angstrom/d').search(self.s4))
        self.failUnless(Query(u'""d').search(self.s4))

    def test_match_diacriticals_dumb(self):
        self.assertTrue(Query(u'Angstrom').search(self.s4))
        self.assertTrue(Query(u'Ångström').search(self.s4))
        self.assertTrue(Query(u'Ångstrom').search(self.s4))
        self.assertFalse(Query(u'Ängström').search(self.s4))

    def test_match_diacriticals_invalid_or_unsupported(self):
        # these fall back to test dumb searches:
        # invalid regex
        Query(u'/Sigur [r-zos/d')
        # group refs unsupported for diacritic matching
        Query(u'/(<)?(\w+@\w+(?:\.\w+)+)(?(1)>)/d')

    def test_numexpr(self):
        self.failUnless(Query("#(length = 224)").search(self.s1))
        self.failUnless(Query("#(length = 3:44)").search(self.s1))
        self.failUnless(Query("#(length = 3 minutes + 44 seconds)")
                        .search(self.s1))
        self.failUnless(Query("#(playcount > skipcount)").search(self.s1))
        self.failUnless(Query("#(playcount < 2 * skipcount)").search(self.s1))
        self.failUnless(Query("#(length > 3 minutes)").search(self.s1))
        self.failUnless(Query("#(3:00 < length < 4:00)").search(self.s1))
        self.failUnless(Query("#(40 seconds < length/5 < 1 minute)")
                        .search(self.s1))
        self.failUnless(Query("#(2+3 * 5 = 17)").search(self.s1))
        self.failUnless(Query("#(playcount / 0 > 0)").search(self.s1))

        self.failIf(Query("#(track + 1 != 13)").search(self.s2))

    def test_numexpr_date(self):
        self.failUnless(Query("#(length < 2005-07-19)").search(self.s1))
        self.failUnless(Query("#(date > 2005-07-19)").search(self.s1))
        self.failUnless(Query("#(2005-11-24 < 2005-07-19)").search(self.s1))
        self.failUnless(Query("#(date = (2007-05-19) + 5 days)")
                        .search(self.s1))
        self.failUnless(Query("#(date - 5 days = 2007-05-19)").search(self.s1))
        self.failUnless(Query("#(2010-02-18 > date)").search(self.s1))
        self.failUnless(Query("#(2010 > date)").search(self.s1))
        self.failUnless(Query("#(date > 4)").search(self.s1))
        self.failUnless(Query("#(date > 0004)").search(self.s1))
        self.failUnless(Query("#(date > 0000)").search(self.s1))


class TQuery_get_type(TestCase):
    def test_red(self):
        for p in ["a = /w", "|(sa#"]:
            self.failUnlessEqual(QueryType.INVALID, Query.get_type(p))

    def test_black(self):
        for p in ["a test", "more test hooray"]:
            self.failUnlessEqual(QueryType.TEXT, Query.get_type(p))

    def test_green(self):
        for p in ["a = /b/", "&(a = b, c = d)", "/abc/", "!x", "!&(abc, def)"]:
            self.failUnlessEqual(QueryType.VALID, Query.get_type(p))
