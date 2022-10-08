# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time

import pytest

from quodlibet import config
from quodlibet.formats import AudioFile
from quodlibet.plugins import Plugin
from quodlibet.plugins.query import QueryPlugin, QUERY_HANDLER
from quodlibet.query import Query, QueryType
from quodlibet.query import _match as match
from senf import fsnative
from tests import TestCase, skip


class TestQuery_is_valid:
    def test_re(self):
        assert Query('t = /an re/').valid
        assert Query('t = /an re/c').valid
        assert Query('t = /an\\/re/').valid
        assert not Query('t = /an/re/').valid
        assert Query('t = /aaa/lsic').valid
        assert not Query('t = /aaa/icslx').valid

    def test_str(self):
        assert Query('t = "a str"').valid
        assert Query('t = "a str"c').valid
        assert Query('t = "a\\"str"').valid
        # there's no equivalent failure for strings since 'str"' would be
        # read as a set of modifiers

    def test_tag(self):
        assert Query('t = tag').valid
        assert Query('t = !tag').valid
        assert Query('t = |(tag, bar)').valid
        assert Query('t = a"tag"').valid
        assert not Query('t = a, tag').valid
        assert Query('tag with spaces = tag').valid

    def test_empty(self):
        assert Query('').valid
        assert Query('').is_parsable
        assert Query('')

    def test_emptylist(self):
        assert not Query("a = &()").valid
        assert not Query("a = |()").valid
        assert not Query("|()").valid
        assert not Query("&()").valid

    def test_nonsense(self):
        assert not Query('a string').valid
        assert not Query('t = #(a > b)').valid
        assert not Query("=a= = /b/").valid
        assert not Query("a = &(/b//").valid
        assert not Query("(a = &(/b//)").valid

    def test_trailing(self):
        assert not Query('t = /an re/)').valid
        assert not Query('|(a, b = /a/, c, d = /q/) woo').valid

    def test_not(self):
        assert Query('t = !/a/').valid
        assert Query('t = !!/a/').valid
        assert Query('!t = "a"').valid
        assert Query('!!t = "a"').valid
        assert Query('t = !|(/a/, !"b")').valid
        assert Query('t = !!|(/a/, !"b")').valid
        assert Query('!|(t = /a/)').valid

    def test_taglist(self):
        assert Query('a, b = /a/').valid
        assert Query('a, b, c = |(/a/)').valid
        assert Query('|(a, b = /a/, c, d = /q/)').valid
        assert not Query('a = /a/, b').valid

    def test_andor(self):
        assert Query('a = |(/a/, /b/)').valid
        assert Query('a = |(/b/)').valid
        assert Query('|(a = /b/, c = /d/)').valid

        assert Query('a = &(/a/, /b/)').valid
        assert Query('a = &(/b/)').valid
        assert Query('&(a = /b/, c = /d/)').valid

    def test_numcmp(self):
        assert Query("#(t < 3)").valid
        assert Query("#(t <= 3)").valid
        assert Query("#(t > 3)").valid
        assert Query("#(t >= 3)").valid
        assert Query("#(t = 3)").valid
        assert Query("#(t != 3)").valid

        assert not Query("#(t !> 3)").valid
        assert not Query("#(t >> 3)").valid

    def test_numcmp_func(self):
        assert Query("#(t:min < 3)").valid
        assert Query("&(#(playcount:min = 0), #(added < 1 month ago))").valid

    def test_trinary(self):
        assert Query("#(2 < t < 3)").valid
        assert Query("#(2 >= t > 3)").valid
        # useless, but valid
        assert Query("#(5 > t = 2)").valid

    def test_list(self):
        assert Query("#(t < 3, t > 9)").valid
        assert Query("t = &(/a/, /b/)").valid
        assert Query("s, t = |(/a/, /b/)").valid
        assert Query("|(t = /a/, s = /b/)").valid

    def test_nesting(self):
        assert Query("|(s, t = &(/a/, /b/),!#(2 > q > 3))").valid

    class FakeQueryPlugin(QueryPlugin):
        PLUGIN_NAME = "name"

        def search(self, song, body):
            return body and "DIE" not in body.upper()

    def test_extension(self):
        plugin = Plugin(self.FakeQueryPlugin)
        QUERY_HANDLER.plugin_enable(plugin)
        try:
            assert Query("@(name)").valid
            assert not Query("@(name: DIE)").search("foo")
            assert Query("@(name: extension body)").valid
            assert Query("@(name: body (with (nested) parens))").valid
            assert Query(r"@(name: body \\ with \) escapes)").valid
        finally:
            QUERY_HANDLER.plugin_disable(plugin)

    def test_extension_search(self):
        plugin = Plugin(self.FakeQueryPlugin)
        QUERY_HANDLER.plugin_enable(plugin)
        song = AudioFile({"~filename": "/dev/null"})
        try:
            assert Query("@(name: LIVE)").search(song)
            assert not Query("@(name: DIE)").search(song)
        finally:
            QUERY_HANDLER.plugin_disable(plugin)

    def test_invalid_extension(self):
        assert not Query("@(name)").valid, "Unregistered plugin is valid"
        assert not Query("@()").valid
        assert not Query(r"@(invalid %name!\\)").valid
        assert not Query("@(name: mismatched ( parenthesis)").valid
        assert not Query(r"@(\()").valid
        assert not Query("@(name:unclosed body").valid
        assert not Query("@ )").valid

    def test_numexpr(self):
        assert Query("#(t < 3*4)").valid
        assert Query("#(t * (1+r) < 7)").valid
        assert Query("#(0 = t)").valid
        assert Query("#(t < r < 9)").valid
        assert Query("#((t-9)*r < -(6*2) = g*g-1)").valid
        assert Query("#(t + 1 + 2 + -4 * 9 > g*(r/4 + 6))").valid
        assert Query("#(date < 2010-4)").valid
        assert Query("#(date < 2010 - 4)").valid
        assert Query("#(date > 0000)").valid
        assert Query("#(date > 00004)").valid
        assert Query("#(added > today)").valid
        assert Query("#(length < 5:00)").valid
        assert Query("#(filesize > 5M)").valid
        assert Query("#(added < 7 days ago)").valid

    def test_numexpr_failures(self):
        assert not Query("#(3*4)").valid
        assert not Query("#(t = 3 + )").valid
        assert not Query("#(t = -)").valid
        assert not Query("#(-4 <)").valid
        assert not Query("#(t < ()").valid
        assert not Query("#((t +) - 1 > 8)").valid
        assert not Query("#(t += 8)").valid

    def test_numexpr_fails_for_wrong_units(self):
        assert not Query("#(t > 3 minutes)").valid
        assert not Query("#(size < 3 minutes)").valid
        assert not Query("#(date = 3 GB)").valid


class TQuery(TestCase):

    def setUp(self):
        config.init()
        self.s1 = AudioFile(
            {"album": u"I Hate: Tests", "artist": u"piman", "title": u"Quuxly",
             "version": u"cake mix",
             "~filename": fsnative(u"/dir1/foobar.ogg"),
             "~#length": 224, "~#skipcount": 13, "~#playcount": 24,
             "date": u"2007-05-24", "~#samplerate": 44100})
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
        assert Query("album!=foo").search(self.s1)
        assert not Query("album!=foo").search(self.s2)

    @skip("Enable for basic benchmarking of Query")
    def test_inequality_performance(self):
        t = time.time()
        for i in range(500):
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
        for i in range(repeats):
            assert Query("album!=foo the bar").search(self.s1)
        ineq_time = (time.time() - t0)
        t1 = time.time()
        for i in range(repeats):
            assert Query("album=!foo the bar").search(self.s1)
        not_val_time = (time.time() - t1)
        assert ineq_time == pytest.approx(not_val_time, abs=0.1)

    def test_repr(self):
        query = Query("foo = bar", [])
        r = repr(query).replace("u'", "'")
        assert r == "<Query string='foo = bar' type=VALID star=[]>"

        query = Query("bar", ["foo"])
        r = repr(query).replace("u'", "'")
        assert r == "<Query string='&(/bar/d)' type=TEXT star=['foo']>"

    def test_2007_07_27_synth_search(self):
        song = AudioFile({"~filename": fsnative(u"foo/64K/bar.ogg")})
        query = Query("~dirname = !64K")
        assert not query.search(song), "%r, %r" % (query, song)

    def test_empty(self):
        assert not Query("foobar = /./").search(self.s1)

    def test_gte(self):
        assert Query("#(track >= 11)").search(self.s2)

    def test_re(self):
        for s in ["album = /i hate/", "artist = /pi*/", "title = /x.y/"]:
            assert Query(s).search(self.s1)
            assert not Query(s).search(self.s2)
        f = Query("artist = /mu|piman/").search
        assert f(self.s1)
        assert f(self.s2)

    def test_re_escape(self):
        af = AudioFile({"foo": "\""})
        assert Query('foo="\\""').search(af)
        af = AudioFile({"foo": "/"})
        assert Query('foo=/\\//').search(af)

    def test_not(self):
        for s in ["album = !hate", "artist = !pi"]:
            assert not Query(s).search(self.s1)
            assert Query(s).search(self.s2)

    def test_abbrs(self):
        for s in ["b = /i hate/", "a = /pi*/", "t = /x.y/"]:
            assert Query(s).search(self.s1)
            assert not Query(s).search(self.s2)

    def test_str(self):
        for k in self.s2.keys():
            v = self.s2[k]
            assert Query('%s = "%s"' % (k, v)).search(self.s2)
            assert not Query('%s = !"%s"' % (k, v)).search(self.s2)

    def test_numcmp(self):
        assert not Query("#(track = 0)").search(self.s1)
        assert not Query("#(notatag = 0)").search(self.s1)
        assert Query("#(track = 12)").search(self.s2)

    def test_trinary(self):
        assert Query("#(11 < track < 13)").search(self.s2)
        assert Query("#(11 < track <= 12)").search(self.s2)
        assert Query("#(12 <= track <= 12)").search(self.s2)
        assert Query("#(12 <= track < 13)").search(self.s2)
        assert Query("#(13 > track > 11)").search(self.s2)
        assert Query("#(20 > track < 20)").search(self.s2)

    def test_not_2(self):
        for s in ["album = !/i hate/", "artist = !/pi*/", "title = !/x.y/"]:
            assert Query(s).search(self.s2)
            assert not Query(s).search(self.s1)

    def test_case(self):
        assert Query("album = /i hate/").search(self.s1)
        assert Query("album = /I Hate/").search(self.s1)
        assert Query("album = /i Hate/").search(self.s1)
        assert Query("album = /i Hate/i").search(self.s1)
        assert Query(u"title = /ångström/").search(self.s4)
        assert not Query("album = /i hate/c").search(self.s1)
        assert not Query(u"title = /ångström/c").search(self.s4)

    def test_re_and(self):
        assert Query("album = &(/ate/,/est/)").search(self.s1)
        assert not Query("album = &(/ate/, /ets/)").search(self.s1)
        assert not Query("album = &(/tate/, /ets/)").search(self.s1)

    def test_re_or(self):
        assert Query("album = |(/ate/,/est/)").search(self.s1)
        assert Query("album = |(/ate/,/ets/)").search(self.s1)
        assert not Query("album = |(/tate/, /ets/)").search(self.s1)

    def test_newlines(self):
        assert Query("a = /\n/").search(self.s3)
        assert Query("a = /\\n/").search(self.s3)
        assert not Query("a = /\n/").search(self.s2)
        assert not Query("a = /\\n/").search(self.s2)

    def test_exp_and(self):
        assert Query("&(album = ate, artist = man)").search(self.s1)
        assert not Query("&(album = ate, artist = nam)").search(self.s1)
        assert not Query("&(album = tea, artist = nam)").search(self.s1)

    def test_exp_or(self):
        assert Query("|(album = ate, artist = man)").search(self.s1)
        assert Query("|(album = ate, artist = nam)").search(self.s1)
        assert not Query("&(album = tea, artist = nam)").search(self.s1)

    def test_dumb_search(self):
        assert Query("ate man").search(self.s1)
        assert Query("Ate man").search(self.s1)
        assert not Query("woo man").search(self.s1)
        assert not Query("not crazy").search(self.s1)

    def test_dumb_search_value(self):
        assert Query("|(ate, foobar)").search(self.s1)
        assert Query("!!|(ate, foobar)").search(self.s1)
        assert Query("&(ate, te)").search(self.s1)
        assert not Query("|(foo, bar)").search(self.s1)
        assert not Query("&(ate, foobar)").search(self.s1)
        assert not Query("! !&(ate, foobar)").search(self.s1)
        assert not Query("&blah").search(self.s1)
        assert Query("&blah oh").search(self.s5)
        assert Query("!oh no").search(self.s5)
        assert not Query("|blah").search(self.s1)
        # https://github.com/quodlibet/quodlibet/issues/1056
        assert Query("&(ate, piman)").search(self.s1)

    def test_dumb_search_value_negate(self):
        assert Query("!xyz").search(self.s1)
        assert Query("!!!xyz").search(self.s1)
        assert Query(" !!!&(xyz, zyx)").search(self.s1)
        assert not Query("!man").search(self.s1)

        assert Query("&(tests,piman)").search(self.s1)
        assert Query("&(tests,!nope)").search(self.s1)
        assert not Query("&(tests,!!nope)").search(self.s1)
        assert not Query("&(tests,!piman)").search(self.s1)
        assert Query("&(tests,|(foo,&(pi,!nope)))").search(self.s1)

    def test_dumb_search_regexp(self):
        assert Query("/(x|H)ate/").search(self.s1)
        assert Query("'PiMan'").search(self.s1)
        assert not Query("'PiMan'c").search(self.s1)
        assert Query("!'PiMan'c").search(self.s1)
        assert not Query("!/(x|H)ate/").search(self.s1)

    def test_unslashed_search(self):
        assert Query("artist=piman").search(self.s1)
        assert Query(u"title=ång").search(self.s4)
        assert not Query("artist=mu").search(self.s1)
        assert not Query(u"title=äng").search(self.s4)

    def test_synth_search(self):
        assert Query("~dirname=/dir1/").search(self.s1)
        assert Query("~dirname=/dir2/").search(self.s2)
        assert not Query("~dirname=/dirty/").search(self.s1)
        assert not Query("~dirname=/dirty/").search(self.s2)

    def test_search_almostequal(self):
        a, b = AudioFile({"~#rating": 0.771}), AudioFile({"~#rating": 0.769})
        assert Query("#(rating = 0.77)").search(a)
        assert Query("#(rating = 0.77)").search(b)

    def test_and_or_neg_operator(self):
        union = Query("|(foo=bar,bar=foo)")
        inter = Query("&(foo=bar,bar=foo)")
        neg = Query("!foo=bar")
        numcmp = Query("#(bar = 0)")
        tag = Query("foo=bar")

        tests = [inter | tag, tag | tag, neg | neg, tag | inter, neg | union,
                 union | union, inter | inter, numcmp | numcmp, numcmp | union]

        assert not [x for x in tests if not isinstance(x, match.Union)]

        tests = [inter & tag, tag & tag, neg & neg, tag & inter, neg & union,
                 union & union, inter & inter, numcmp & numcmp, numcmp & inter]

        assert not [x for x in tests if not isinstance(x, match.Inter)]

        assert isinstance(-neg, match.Tag)

        true = Query("")
        assert isinstance(true | inter, match.True_)
        assert isinstance(inter | true, match.True_)
        assert isinstance(true & inter, match.Inter)
        assert isinstance(inter & true, match.Inter)
        assert isinstance(true & true, match.True_)
        assert isinstance(true | true, match.True_)
        assert isinstance(-true, match.Neg)

    def test_filter(self):
        q = Query("artist=piman")
        assert q.filter([self.s1, self.s2]) == [self.s1]
        assert q.filter(iter([self.s1, self.s2])) == [self.s1]

        q = Query("")
        assert q.filter([self.s1, self.s2]), [self.s1 == self.s2]
        assert q.filter(iter([self.s1, self.s2])), [self.s1 == self.s2]

    def test_match_all(self):
        assert Query("").matches_all
        assert Query("    ").matches_all
        assert not Query("foo").matches_all

    def test_utf8(self):
        # also handle undecoded values
        assert Query(u"utf8=Ångström").search(self.s4)

    def test_fs_utf8(self):
        assert Query(u"~filename=foü.ogg").search(self.s3)
        assert Query(u"~filename=öä").search(self.s3)
        assert Query(u"~dirname=öäü").search(self.s3)
        assert Query(u"~basename=ü.ogg").search(self.s3)

    def test_filename_utf8_fallback(self):
        assert Query(u"filename=foü.ogg").search(self.s3)
        assert Query(u"filename=öä").search(self.s3)

    def test_mountpoint_utf8_fallback(self):
        assert Query(u"mountpoint=foü").search(self.s3)
        assert Query(u"mountpoint=öä").search(self.s3)

    def test_mountpoint_no_value(self):
        af = AudioFile({"~filename": fsnative(u"foo")})
        assert not Query(u"~mountpoint=bla").search(af)

    def test_star_numeric(self):
        with pytest.raises(ValueError):
            Query(u"foobar", star=["~#mtime"])

    def test_match_diacriticals_explcit(self):
        assert Query(u'title=angstrom').search(self.s4)
        assert not Query(u'title="Ångstrom"').search(self.s4)
        assert Query(u'title="Ångstrom"d').search(self.s4)
        assert Query(u'title=Ångström').search(self.s4)
        assert Query(u'title="Ångström"').search(self.s4)
        assert Query(u'title=/Ångström/').search(self.s4)
        assert Query(u'title="Ångstrom"d').search(self.s4)
        assert Query(u'title=/Angstrom/d').search(self.s4)
        assert Query(u'""d').search(self.s4)

    def test_match_diacriticals_dumb(self):
        assert Query(u'Angstrom').search(self.s4)
        assert Query(u'Ångström').search(self.s4)
        assert Query(u'Ångstrom').search(self.s4)
        assert not Query(u'Ängström').search(self.s4)

    def test_match_diacriticals_invalid_or_unsupported(self):
        # these fall back to test dumb searches:
        # invalid regex
        Query(u'/Sigur [r-zos/d')
        # group refs unsupported for diacritic matching
        Query(u'/(<)?(\\w+@\\w+(?:\\.\\w+)+)(?(1)>)/d')

    def test_numexpr(self):
        assert Query("#(length = 224)").search(self.s1)
        assert Query("#(length = 3:44)").search(self.s1)
        assert Query("#(length = 3 minutes + 44 seconds)").search(self.s1)
        assert Query("#(playcount > skipcount)").search(self.s1)
        assert Query("#(playcount < 2 * skipcount)").search(self.s1)
        assert Query("#(length > 3 minutes)").search(self.s1)
        assert Query("#(3:00 < length < 4:00)").search(self.s1)
        assert Query("#(40 seconds < length/5 < 1 minute)").search(self.s1)
        assert Query("#(2+3 * 5 = 17)").search(self.s1)
        assert Query("#(playcount / 0 > 0)").search(self.s1)

        assert not Query("#(track + 1 != 13)").search(self.s2)

    def test_numexpr_date(self):
        assert Query("#(length < 2005-07-19)").search(self.s1)
        assert Query("#(date > 2005-07-19)").search(self.s1)
        assert Query("#(2005-11-24 < 2005-07-19)").search(self.s1)
        assert Query("#(date = (2007-05-19) + 5 days)").search(self.s1)
        assert Query("#(date - 5 days = 2007-05-19)").search(self.s1)
        assert Query("#(2010-02-18 > date)").search(self.s1)
        assert Query("#(2010 > date)").search(self.s1)
        assert Query("#(date > 4)").search(self.s1)
        assert Query("#(date > 0004)").search(self.s1)
        assert Query("#(date > 0000)").search(self.s1)

    def test_large_numbers(self):
        assert Query("#(playcount = 00024)").search(self.s1)
        assert Query("#(samplerate = 44100)").search(self.s1)

    def test_ignore_characters(self):
        try:
            config.set("browsers", "ignored_characters", "-")
            assert Query("Foo the Bar - mu").search(self.s2)
            config.set("browsers", "ignored_characters", "1234")
            assert Query("4Fo13o 2th2e3 4Bar4").search(self.s2)
        finally:
            config.reset("browsers", "ignored_characters")


class TestQuery_get_type:
    def test_red(self):
        for p in ["a = /w", "|(sa#"]:
            assert Query(p).type == QueryType.INVALID

    def test_black(self):
        for p in ["a test", "more test hooray"]:
            assert Query(p).type == QueryType.TEXT

    def test_green(self):
        for p in ["a = /b/", "&(a = b, c = d)", "/abc/", "!x", "!&(abc, def)"]:
            assert Query(p).type == QueryType.VALID
