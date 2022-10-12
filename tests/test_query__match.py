# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import pytest
from quodlibet.formats import AudioFile
from quodlibet.query._match import NumexprNow, numexprTagOrSpecial, Inter, True_, Neg
from quodlibet.query._match import numexprUnit, ParseError, NumexprTag, Numcmp
from quodlibet.util import parse_date
from quodlibet.util.collection import Collection
from tests import TestCase


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
        assert numexprUnit(10, 'seconds').evaluate(None, 0, True) == 10
        assert numexprUnit(10, 'minutes').evaluate(None, 0, True) == 10 * 60
        assert numexprUnit(1, 'year').evaluate(None, 0, True) == 365 * 24 * 60 * 60
        assert numexprUnit(3, 'k').evaluate(None, 0, True) == 3 * 1024
        assert numexprUnit(3, 'megabytes').evaluate(None, 0, True) == 3 * 1024 ** 2

    def test_numexpr_raises_for_invalid_units(self):
        with pytest.raises(ParseError):
            numexprUnit(7, 'invalid unit')

    def test_time_tag(self):
        time = 424242
        song = AudioFile({'~#added': 400000, '~#mtime': 410000, '~#length': 315})
        added_value = NumexprTag('added').evaluate(song, time, True)
        assert added_value == 24242
        assert NumexprTag('length').evaluate(song, time, True) == 315
        assert NumexprTag('date').evaluate(song, time, True) is None
        assert added_value > NumexprTag('mtime').evaluate(song, time, True)

    def test_date_tag(self):
        time = 424242
        song = AudioFile({'date': '2012-11-09'})
        date_value = NumexprTag('date').evaluate(song, 0, True)
        assert date_value == parse_date('2012-11-09')
        assert NumexprTag('date').evaluate(song, time, True) == parse_date('2012-11-09')
        assert date_value > parse_date('2012-11-08')
        assert date_value < parse_date('2012-11-10')

    def test_numexpr_func(self):
        time = 424242
        col = Collection()
        col.songs = (AudioFile({'~#added': 400000, '~#length': 315}),
                     AudioFile({'~#added': 405000, '~#length': 225}))
        assert NumexprTag('length:avg').evaluate(col, time, True) == 270
        assert NumexprTag('added:max').evaluate(col, time, True) == 19242

    def test_numcmp_with_aggregate_and_units(self):
        col = Collection()
        col.songs = (AudioFile({'~#length': 30}), AudioFile({'~#length': 210}))
        min_length = NumexprTag('length:min')
        max_length = NumexprTag('length:max')
        avg_length = NumexprTag('length:avg')
        assert Numcmp(min_length, ">", numexprUnit(10, "seconds"))
        assert Numcmp(min_length, "<", numexprUnit(2, "minutes"))
        assert Numcmp(max_length, "<", numexprUnit(1, "hour"))
        assert Numcmp(max_length, ">=", numexprUnit(30, "seconds"))
        assert Numcmp(avg_length, "=", numexprUnit(2, "minutes"))

    def test_numexpr_now(self):
        time = 424242
        day = 24 * 60 * 60
        now_none = NumexprNow().evaluate(None, time, True)
        assert now_none == time
        today_none = NumexprNow(day).evaluate(None, time, True)
        assert today_none == time - day
        assert now_none == numexprTagOrSpecial('now').evaluate(None, time, True)
        assert today_none == numexprTagOrSpecial('today').evaluate(None, time, True)
        assert repr(NumexprNow()) == repr(numexprTagOrSpecial('now'))
        assert repr(NumexprTag('genre')) == repr(numexprTagOrSpecial('genre'))
