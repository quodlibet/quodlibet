# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.query._match import numexprUnit, ParseError, NumexprTag
from quodlibet.query._match import NumexprNow, numexprTagOrSpecial, Inter,\
    True_, Neg
from quodlibet.util import parse_date
from quodlibet.formats import AudioFile
from quodlibet.util.collection import Collection


class TQueryInter(TestCase):

    def test_main(self):
        q = Inter([])
        assert q.filter([1]) == [1]
        q = Inter([True_()])
        assert q.filter([1]) == [1]
        q = Inter([True_(), True_()])
        assert q.filter([1]) == [1]
        q = Inter([True_(), Neg(True_())])
        assert q.filter([1]) == []
        q = Inter([Neg(True_()), True_()])
        assert q.filter([1]) == []
        q = Inter([Neg(True_())])
        assert q.filter([1]) == []


class TQueryMatch(TestCase):

    def test_numexpr_unit(self):
        self.failUnless(numexprUnit(10, 'seconds').evaluate(None, 0, True)
                        == 10)
        self.failUnless(numexprUnit(10, 'minutes').evaluate(None, 0, True)
                        == 10 * 60)
        self.failUnless(numexprUnit(1, 'year').evaluate(None, 0, True)
                        == 365 * 24 * 60 * 60)
        self.failUnless(numexprUnit(3, 'k').evaluate(None, 0, True)
                        == 3 * 1024)
        self.failUnless(numexprUnit(3, 'megabytes').evaluate(None, 0, True)
                        == 3 * 1024 ** 2)
        self.failUnlessRaises(ParseError, numexprUnit, 7, 'invalid unit')

    def test_time_tag(self):
        time = 424242
        song = AudioFile({'~#added': 400000, '~#mtime': 410000,
                          '~#length': 315})
        self.failUnless(NumexprTag('added').evaluate(song, time, True)
                        == 24242)
        self.failUnless(NumexprTag('length').evaluate(song, time, True) == 315)
        self.failUnless(NumexprTag('date').evaluate(song, time, True) is None)
        self.failUnless(NumexprTag('added').evaluate(song, time, True)
                        > NumexprTag('mtime').evaluate(song, time, True))

    def test_date_tag(self):
        song = AudioFile({'date': '2012-11-09'})
        self.failUnless(NumexprTag('date').evaluate(song, 0, True)
                        == parse_date('2012-11-09'))
        self.failUnless(NumexprTag('date').evaluate(song, 424242, True)
                        == parse_date('2012-11-09'))
        self.failUnless(NumexprTag('date').evaluate(song, 0, True)
                        > parse_date('2012-11-08'))
        self.failUnless(NumexprTag('date').evaluate(song, 0, True)
                        < parse_date('2012-11-10'))

    def test_numexpr_func(self):
        time = 424242
        col = Collection()
        col.songs = (AudioFile({'~#added': 400000, '~#length': 315}),
                     AudioFile({'~#added': 405000, '~#length': 225}))
        self.failUnless(NumexprTag('length:avg').evaluate(col, time, True)
                        == 270)
        self.failUnless(NumexprTag('added:max').evaluate(col, time, True)
                        == 19242)

    def test_numexpr_now(self):
        time = 424242
        day = 24 * 60 * 60
        self.failUnless(NumexprNow().evaluate(None, time, True) == time)
        self.failUnless(NumexprNow(day).evaluate(None, time, True)
                        == time - day)
        self.failUnless(NumexprNow().evaluate(None, time, True) ==
                        numexprTagOrSpecial('now').evaluate(None, time, True))
        self.failUnless(NumexprNow(day).evaluate(None, time, True) ==
                        numexprTagOrSpecial('today')
                        .evaluate(None, time, True))
        self.failUnless(NumexprNow().__repr__()
                        == numexprTagOrSpecial('now').__repr__())
        self.failUnless(NumexprTag('genre').__repr__()
                        == numexprTagOrSpecial('genre').__repr__())
