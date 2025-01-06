# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.util.string.splitters import (
    split_value,
    split_title,
    split_album,
    split_people,
    split_genre,
)


class Tsplit_value(TestCase):
    def test_single(self):
        self.assertEqual(split_value("a b"), ["a b"])

    def test_double(self):
        self.assertEqual(split_value("a, b"), ["a", "b"])

    def test_custom_splitter(self):
        self.assertEqual(split_value("a b", [" "]), ["a", "b"])

    def test_two_splitters(self):
        self.assertEqual(split_value("a, b and c", [",", "and"]), ["a", "b and c"])

    def test_no_splitters(self):
        self.assertEqual(split_value("a b", []), ["a b"])

    def test_word_boundary(self):
        self.assertEqual(
            split_value("Andromeda and the Band", ["and"]), ["Andromeda", "the Band"]
        )

    def test_non_word_preceding(self):
        # See #2678
        actual = split_value("Dan Vickrey (1966-); Ben Mize", [";"])
        self.assertEqual(actual, ["Dan Vickrey (1966-)", "Ben Mize"])

        # See #1088
        self.assertEqual(
            split_value("[dialogue],Red Elvises"), ["[dialogue]", "Red Elvises"]
        )

    def test_non_word_following(self):
        self.assertEqual(
            split_value("Red Elvises , [dialogue]", ","), ["Red Elvises", "[dialogue]"]
        )

    def test_unicode_word_boundary(self):
        val = b"\xe3\x81\x82&\xe3\x81\x84".decode("utf-8")
        self.assertEqual(split_value(val), val.split("&"))


class Tsplit_title(TestCase):
    def test_trailing(self):
        self.assertEqual(split_title("foo ~"), ("foo ~", []))

    def test_prefixed(self):
        self.assertEqual(split_title("~foo "), ("~foo ", []))

    def test_prefix_and_trailing(self):
        self.assertEqual(split_title("~foo ~"), ("~foo ~", []))

    def test_prefix_and_version(self):
        self.assertEqual(split_title("~foo ~bar~"), ("~foo", ["bar"]))

    def test_simple(self):
        self.assertEqual(split_title("foo (baz)"), ("foo", ["baz"]))

    def test_two_versions(self):
        self.assertEqual(split_title("foo [b, c]"), ("foo", ["b", "c"]))

    def test_custom_splitter(self):
        self.assertEqual(split_title("foo [b c]", " "), ("foo", ["b", "c"]))

    def test_custom_subtag_splitter(self):
        self.assertEqual(split_title("foo |b c|", " ", ["||"]), ("foo", ["b", "c"]))
        self.assertEqual(split_title("foo abc", " ", ["ac"]), ("foo", ["b"]))
        self.assertEqual(split_title("foo (a)", " ", []), ("foo (a)", []))


class Tsplit_album(TestCase):
    def test_album_looks_like_disc(self):
        self.assertEqual(split_album("disk 2"), ("disk 2", None))

    def test_basic_disc(self):
        self.assertEqual(split_album("foo disc 1/2"), ("foo", "1/2"))

    def test_looks_like_disc_but_isnt(self):
        self.assertEqual(split_album("disc foo disc"), ("disc foo disc", None))

    def test_disc_album_and_disc(self):
        self.assertEqual(split_album("disc foo disc 1"), ("disc foo", "1"))

    def test_weird_disc(self):
        self.assertEqual(split_album("foo ~disk 3~"), ("foo", "3"))

    def test_weird_not_disc(self):
        self.assertEqual(split_album("foo ~crazy 3~"), ("foo ~crazy 3~", None))

    def test_custom_splitter(self):
        self.assertEqual(split_album("foo |CD 1|", ["||"]), ("foo", "1"))


class Tsplit_people(TestCase):
    def test_parened_person(self):
        self.assertEqual(split_people("foo (bar)"), ("foo", ["bar"]))

    def test_with_person(self):
        self.assertEqual(split_people("foo (With bar)"), ("foo", ["bar"]))

    def test_with_with_person(self):
        self.assertEqual(split_people("foo (with with bar)"), ("foo", ["with bar"]))

    def test_featuring_two_people(self):
        self.assertEqual(split_people("foo featuring bar, qx"), ("foo", ["bar", "qx"]))

    def test_featuring_person_bracketed(self):
        self.assertEqual(split_people("foo (Ft. bar)"), ("foo", ["bar"]))
        self.assertEqual(split_people("foo(feat barman)"), ("foo", ["barman"]))

    def test_originally_by(self):
        self.assertEqual(
            split_people("title (originally by artist)"), ("title", ["artist"])
        )
        self.assertEqual(
            split_people("title [originally by artist & artist2]"),
            ("title", ["artist", "artist2"]),
        )

    def test_cover(self):
        self.assertEqual(
            split_people("Psycho Killer [Talking Heads Cover]"),
            ("Psycho Killer", ["Talking Heads"]),
        )

    def test_custom_splitter(self):
        self.assertEqual(split_people("foo |With bar|", " ", ["||"]), ("foo", ["bar"]))


class Tsplit_genre(TestCase):
    def test_single(self):
        assert split_genre("New Age") == ["New Age"]

    def test_genre_semicolon(self):
        genres = split_genre("rock ; rap; country;pop ;techno;metal", tag_splitters=";")
        assert genres == ["rock", "rap", "country", "pop", "techno", "metal"]

    def test_genre_comma(self):
        genres = split_genre("rock , rap, country,pop ,techno,metal")
        assert genres == ["rock", "rap", "country", "pop", "techno", "metal"]

    def test_genre_ampersand(self):
        genres = split_genre("rock & rap& country&pop & techno &metal")
        assert genres == ["rock", "rap", "country", "pop", "techno", "metal"]

    def test_genre_slash(self):
        genres = split_genre(" rock / rap/ country/pop /techno/metal")
        assert genres == ["rock", "rap", "country", "pop", "techno", "metal"]

    def test_genre_slash_before_comma(self):
        # slash should be interpreted AFTER a comma
        genres = split_genre(" Indie/Rock, Country, Alt/Country ")
        assert genres == ["Indie/Rock", "Country", "Alt/Country"]
