# -*- coding: utf-8 -*-
# Copyright 2010 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

from tests import TestCase, add

from quodlibet.util.fmps import *

class TFmps(TestCase):
    def setUp(self):
        pass

    def test_float(self):
        self.failUnlessEqual(str(FmpsFloat(1.0)), "1.0")
        self.failUnlessEqual(str(FmpsFloat(0.0)), "0.0")
        self.failUnlessEqual(str(FmpsFloat(-1.0)), "-1.0")
        self.failUnlessEqual(str(FmpsFloat(1.123456789)), "1.123457")

    def test_parse_float(self):
        self.failUnlessRaises(ValueError, lambda: FmpsFloat(""))
        self.failUnlessRaises(ValueError, lambda: FmpsFloat("a"))

        self.failUnlessEqual(FmpsFloat("99.99").native(), 99.99)
        self.failUnlessEqual(FmpsFloat("-1.0").native(), -1.0)
        self.failUnlessEqual(FmpsFloat("-1").native(), -1)

    def test_pos_float(self):
        self.failUnlessEqual(str(FmpsPositiveFloat(1.0)), "1.0")
        self.failUnlessEqual(str(FmpsPositiveFloat(0.0)), "0.0")
        self.failUnlessEqual(str(FmpsPositiveFloat(1.123456789)), "1.123457")
        self.failUnlessRaises(ValueError, lambda: FmpsPositiveFloat(-1.0))
        self.failUnlessRaises(
            ValueError, lambda: FmpsPositiveFloat(4294967295))

    def test_parse_pos_float(self):
        self.failUnlessRaises(ValueError, lambda: FmpsPositiveFloat(""))
        self.failUnlessRaises(ValueError, lambda: FmpsPositiveFloat("a"))
        self.failUnlessRaises(ValueError, lambda: FmpsPositiveFloat("-1.0"))

        self.failUnlessEqual(FmpsPositiveFloat("99.99").native(), 99.99)
        self.failUnlessEqual(
            FmpsPositiveFloat("4294967296").native(), 4294967296)

    def test_rating_float(self):
        self.failUnlessEqual(str(FmpsRatingFloat(1.0)), "1.0")
        self.failUnlessEqual(str(FmpsRatingFloat(1)), "1.0")
        self.failUnlessRaises(ValueError, lambda: FmpsRatingFloat(-1.0))
        self.failUnlessRaises(ValueError, lambda: FmpsRatingFloat(1.1))

    def test_parse_rating_float(self):
        self.failUnlessRaises(ValueError, lambda: FmpsRatingFloat(""))
        self.failUnlessRaises(ValueError, lambda: FmpsRatingFloat("a"))
        self.failUnlessRaises(ValueError, lambda: FmpsRatingFloat("-1.0"))
        self.failUnlessRaises(ValueError, lambda: FmpsRatingFloat("1.1"))

        self.failUnlessEqual(FmpsRatingFloat("1").native(), 1)
        self.failUnlessEqual(FmpsRatingFloat("0.0").native(), 0)

    def test_rating_user(self):
        a = RatingUser("Alice Abba::0.6;;Bob Beatles::0.8;;Alice Abba::0.6")
        self.failUnlessEqual(a.get_all("Alice"), [])
        self.failUnlessEqual(a.keys(), ["Alice Abba", "Bob Beatles"])
        self.failUnlessEqual(a.get_all("Alice Abba"), [0.6, 0.6])
        a.remove_all("Alice Abba")
        self.failUnlessEqual(a.get_all("Alice Abba"), [])
        self.failUnlessEqual(a.keys(), ["Bob Beatles"])
        a.set_all("Bob Beatles", 0.25)
        self.failUnlessEqual(a.to_data(), "Bob Beatles::0.25")
        a.append("Bob Beatles", 0.5)
        a.extend("Bob Beatles", [0.75, 1])
        self.failUnlessEqual(a.get_all("Bob Beatles"), [0.25, 0.5, 0.75, 1])
        a.set_all("Bob Beatles", [0.125, 0.375])
        self.failUnlessEqual(a.get_all("Bob Beatles"), [0.125, 0.375])
        self.failUnlessEqual(a.to_data(),
            "Bob Beatles::0.125;;Bob Beatles::0.375")

    def test_rating_user_2(self):
        # if a key got invalid values it still shows up, but returns an
        # empty list
        a = RatingUser("foo::1.25;;bar::0.75;;foo::-1")
        self.failUnlessEqual(a.keys(), ["foo", "bar"])
        self.failUnlessEqual(a.get_all("foo"), [])
        # also they will be written back
        self.failUnlessEqual(a.to_data(), "foo::1.25;;foo::-1;;bar::0.75")
        # but they will be overwritten
        a.set_all("foo", 0.25)
        self.failUnlessEqual(a.to_data(), "foo::0.25;;bar::0.75")

    def test_rating_user_3(self):
        a = RatingUser("a::b::c;;abc;;def")
        a.append("foo", 0.25)
        self.failUnlessEqual(a.to_data(), "foo::0.25;;a::b::c;;abc;;def")

        # ignore empty strings
        a = RatingUser("")
        a.append("foo", 0.25)
        self.failUnlessEqual(a.to_data(), "foo::0.25")

    def test_rating_user_4(self):
        a = RatingUser("foo::0.5")
        self.failUnlessRaises(ValueError, lambda: a.set_all("foo", 1.2))
        # an error shouldn't remove old data
        self.failUnlessEqual(a.to_data(), "foo::0.5")

    def test_rating_user_5(self):
        a = RatingUser()
        x = [1, 0]
        y = x[:]
        a.set_all("x",x)
        self.failUnlessEqual(x, y)

    def test_int(self):
        a = Playcount("3.0000")
        self.failUnlessEqual(type(a.native()), int)
        self.failUnlessEqual(str(a), "3.0000")

        a = PlaycountUser("a::135.0;;b::123")
        self.failUnlessEqual(a.get_all("a"), [135])
        self.failUnlessEqual(a.get_all("b"), [123])

    def test_key(self):
        a = PlaycountUser()
        self.failUnlessRaises(ValueError, lambda: a.set_all("", 1.0))
        self.failUnlessRaises(ValueError, lambda: a.append("", 1.0))
        a = RatingUser()
        self.failUnlessRaises(ValueError, lambda: a.set_all("", 1.0))
        self.failUnlessRaises(ValueError, lambda: a.append("", 1.0))

    def test_escaping(self):
        a = RatingUser()
        a.extend("foo::;;", [0, 0])
        self.failUnlessEqual(a.to_data(),
            r"foo\:\:\;\;::0.0;;foo\:\:\;\;::0.0")

        a = RatingUser(r"foo\:\:\;\;::0.0;;foo\:\:\;\;::0.0")
        self.failUnlessEqual(a.get_all("foo::;;"), [0, 0])

        a = Performers()
        a.set_all(";;foo::", ["::bar;;", r"\;\;\:\:", r"\:\:\;\;"])
        b = Performers(a.to_data())
        self.failUnlessEqual(a.to_data(), b.to_data())

    def test_escaping_2(self):
        d = "a::b;;;c::d"
        a = RatingUser(d)
        self.failUnlessEqual(a.to_data(), d)

        d = "a::b;;c:::d"
        a = RatingUser(d)
        self.failUnlessEqual(a.to_data(), d)

        d = ";;;;"
        a = RatingUser(d)
        self.failUnlessEqual(a.to_data(), "")

    def test_escaping_3(self):
        a = RatingUser(":;:;:;::1")
        self.failUnlessEqual(a.to_data(), r"\:\;\:\;\:\;::1")

        a = Performers(":;::;:;")
        self.failUnlessEqual(a.to_data(), r"\:\;::\;\:\;")

    def test_escaping_4(self):
        a = Performers(";x;;a::b;;:;")
        Performers(a.to_data())
        Performers(a.to_data())
        Performers(a.to_data())
        self.failUnlessEqual(a.get_all("a"), ["b"])

    def test_escaping_5(self):
        a = Performers(r"a::b\;;a\::b")
        self.failUnlessEqual(a.get_all("a"), ["b;;a::b"])
        a = Performers(r"a::b\\;;a\\::b")
        self.failUnlessEqual(a.get_all("a"), ["b\\"])
        self.failUnlessEqual(a.get_all("a\\"), ["b"])
        a = Performers(r"ab::b\\\;;a\\\::b")
        self.failUnlessEqual(a.get_all("ab"), [r"b\;;a\::b"])
        self.failUnlessEqual(a.to_data(), r"ab::b\\\;\;a\\\:\:b")
        a = Performers(r"a::b\\\\;;a\\\\::b")
        self.failUnlessEqual(a.get_all("a"), ["b\\\\"])
        self.failUnlessEqual(a.get_all("a\\\\"), ["b"])
        a = Performers(r"a::b;;;a::b;;;a::b")
        self.failUnlessEqual(a.get_all("a"), [])
        a = Performers(r":a::b;;a::b;;;a::b")
        self.failUnlessEqual(a.get_all(":a"), ["b"])
        a = Performers(r";:a::b;;a::b;;;a::b")
        self.failUnlessEqual(a.get_all(";:a"), ["b"])

    def test_escaping_6(self):
        a = Performers(r";;")
        self.failUnlessEqual(a.to_data(), "")

    def test_invalid_escaping(self):
        d = r"in:;;:va;\;li\;d\;:\:\:\x."
        a = Performers(d)
        self.failUnlessEqual(a.to_data(), d)

        a = RatingUser(r"foo::ba:\:\;;;foo::\:")
        self.failUnlessEqual(a.to_data(), r"foo::ba\:\:\;;;foo::\:")

    def test_merge(self):
        a = Performers(["ab::cd", "ef::gh"])
        self.failUnlessEqual(a.get_all("ab"), ["cd"])
        self.failUnlessEqual(a.get_all("ef"), ["gh"])
        self.failUnlessEqual(a.to_data(), "ab::cd;;ef::gh")

        a = Performers(["ab::cd", ";ef::gh;;ab::x", ";a;;;c"])
        self.failUnlessEqual(a.get_all("ab"), ["cd", "x"])
        self.failUnlessEqual(a.get_all(";ef"), ["gh"])
        self.failUnlessEqual(a.to_data(), "\\;ef::gh;;ab::cd;;ab::x;;\\;a;;;c")
        a = Performers(a.to_data())
        self.failUnlessEqual(a.get_all("ab"), ["cd", "x"])
        self.failUnlessEqual(a.get_all(";ef"), ["gh"])

    def test_rating_algo(self):
        a = RatingAlgorithm("")
        self.failUnlessEqual(a.keys(), [])

        a = RatingAlgorithm("a::b::0;;a::c::1.0;;a::b::0.25")
        self.failUnlessEqual(a.keys(), ["a"])
        self.failUnlessEqual(a.get_all("a"), {"b": [0, 0.25], "c": [1]})
        self.failUnlessEqual(a.get_all("a", "c"),[1])

    def test_rating_algo_2(self):
        a = RatingAlgorithm("a::b::0;;a::c::1.0;;a::b::0.25")
        a.remove_all("a", "c")
        self.failUnlessEqual(a.keys(), ["a"])
        self.failUnlessEqual(a.get_all("a"), {"b": [0,0.25]})
        a.remove_all("a")
        self.failUnlessEqual(a.keys(), [])
        self.failUnlessEqual(a.to_data(), "")

    def test_rating_algo_3(self):
        a = RatingAlgorithm("a::b::0")
        x = {"d": 1}
        y = {"d": 1}
        a.set_all("a", None, x)
        self.failUnlessEqual(x, y)
        self.failUnlessEqual(a.to_data(), "a::d::1.0")

        a.remove_all("a")
        x = [0, 0.25]
        y = x[:]
        a.set_all("x", "y", x)
        a.set_all("x", "y", x)
        self.failUnlessEqual(x, y)
        self.failUnlessEqual(a.to_data(), "x::y::0.0;;x::y::0.25")

    def test_rating_algo_4(self):
        a = RatingAlgorithm("a::b::0")
        a.append("a", "b", 1)
        a.append("a", "c", 1)
        self.failUnlessEqual(a.get_all("a"), {"b": [0, 1], "c": [1]})

        a.remove_all("a")
        a.extend("a", "b", [0, 1])
        self.failUnlessEqual(a.to_data(), "a::b::0.0;;a::b::1.0")

    def test_rating_algo_5(self):
        a = RatingAlgorithm("a::b::0;;a::b::1")
        self.failUnlessEqual(a.items(), [("a", "b", 0), ("a", "b", 1)])

        a = RatingAlgorithm()
        self.failUnlessEqual(a.get_all("foo"), {})
        self.failUnlessEqual(a.get_all("foo", "bar"), [])

    def test_escaping_20(self):
        a = RatingAlgorithm()
        a.extend("foo::;;", ":;::", [0])
        self.failUnlessEqual(a.to_data(),
            r"foo\:\:\;\;::\:\;\:\:::0.0")

        a = RatingAlgorithm(r"foo\:\:\;\;::;\:::0.0")
        self.failUnlessEqual(a.get_all("foo::;;", ";:"), [0])

    def test_invalid_escaping_20(self):
        d = r"in:;;:va;\;li\;d\;:\:\:"
        a = AlbumsCompilations(d)
        self.failUnlessEqual(a.to_data(), d)

        a = AlbumsCompilations(r"fo:o::ba:\:::;x;:;;xxx")
        self.failUnlessEqual(a.to_data(), r"fo\:o::ba\:\:::\;x\;\:;;xxx")

    def test_invalid_escaping_21(self):
        a = AlbumsCompilations(r";xxx;;a::b::c;;x;")
        a = AlbumsCompilations(a.to_data())
        a = AlbumsCompilations(a.to_data())
        a = AlbumsCompilations(a.to_data())
        self.failUnlessEqual(a.get_all("a", "b"), ["c"])

add(TFmps)
