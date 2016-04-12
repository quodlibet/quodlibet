# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.query._match import numexprUnit, ParseError, NumexprTag
from quodlibet.query._match import NumexprNow, numexprTagOrSpecial
from quodlibet.util import parse_date
from quodlibet.formats import AudioFile


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
