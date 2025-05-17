# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import re
import unicodedata

from tests import TestCase

from quodlibet.unisearch import compile
from quodlibet.unisearch.db import diacritic_for_letters
from quodlibet.unisearch.parser import re_replace_literals, re_add_variants


class TUniSearch(TestCase):
    def test_mapping(self):
        cache = diacritic_for_letters(False)
        new = diacritic_for_letters(True)
        self.assertEqual(sorted(cache.items()), sorted(new.items()))

    def test_normalize_input(self):
        assert re.match(re_add_variants(unicodedata.normalize("NFD", "ö")), "ö")

    def test_re_replace(self):
        r = re_add_variants("aa")
        assert "[" in r and "]" in r and r.count("ä") == 2

    def test_re_replace_multi(self):
        r = re_add_variants("ae")
        self.assertEqual(
            r,
            "(?:[aàáâãäåāăąǎǟǡǻȁȃȧḁạảấầẩẫậắằẳẵặ][eèéêëēĕėęěȅȇȩḕḗḙḛḝẹẻẽếềểễệ]|[æǣǽ])",
        )

        r = re_add_variants("SS")
        self.assertEqual(r, "(?:[SŚŜŞŠȘṠṢṤṦṨꞄ][SŚŜŞŠȘṠṢṤṦṨꞄ]|ẞ)")

        r = re_add_variants("ss")
        self.assertEqual(r, "(?:[sśŝşšșṡṣṥṧṩꞅ][sśŝşšșṡṣṥṧṩꞅ]|ß)")

    def test_punct(self):
        r = re_add_variants("'")
        assert "`" in r
        assert "'" in r
        r = re_add_variants("''")
        assert '"' in r
        r = re_add_variants('"')
        assert "”" in r
        assert "“" in r
        r = re_add_variants("\\*")
        assert re.match(r, "*")

    def test_re_replace_multi_fixme(self):
        # we don't handler overlapping sequences, so this doesn't match "LỺ"
        r = re_add_variants("LLL")
        self.assertEqual(r, "(?:[LĹĻĽḶḸḺḼŁ][LĹĻĽḶḸḺḼŁ]|Ỻ)[LĹĻĽḶḸḺḼŁ]")

    def test_re_replace_multi_nested(self):
        r = re_add_variants("(եւ)")
        self.assertEqual(r, "((?:եւ|և))")
        r = re_add_variants("(եւ)+")
        self.assertEqual(r, "((?:եւ|և))+")

    def test_re_replace_escape(self):
        r = re_add_variants("n\\n")
        self.assertEqual(r, "[nñńņňǹṅṇṉṋŉ]\n")

    def test_construct_regexp(self):
        res = [
            ("\\.", None),
            ("..", None),
            ("\\.", None),
            ("^a\aa[ha-z]k{1,3}h*h+h?(x|yy)(a+b|cd)$", None),
            ("(?=Asimov)", None),
            ("(?!Asimov)", None),
            ("(?<=abc)def", None),
            ("(?<!foo)", None),
            ("(?#foo)", ""),
            ("(.+) \1", None),
            (
                "\\A\\b\\B\\d\\D\\s\\S\\w\\W\\Z\a",
                "\\A\\b\\B[\\d][\\D][\\s][\\S][\\w][\\W]\\Z\a",
            ),
            ("a{3,5}?a+?a*?a??", None),
            ("^foo$", None),
            (
                "[-+]?(\\d+(\\.\\d*)?|\\.\\d+)([eE][-+]?\\d+)?",
                "[\\-\\+]?([\\d]+(\\.[\\d]*)?|\\.[\\d]+)([eE][\\-\\+]?[\\d]+)?",
            ),
            ("(\\$\\d*)", "(\\$[\\d]*)"),
            ("\\$\\.\\^\\[\\]\\:\\-\\+\\?\\\\", None),
            ("[^a][^ab]", None),
            ("[ab][abc]", None),
            ("[.]", "\\."),
            ("[^a-z]", None),
            ("[^a-z\\w]", None),
            ("(x|yy)", None),
        ]

        for r, o in res:
            if o is None:
                o = r
            self.assertEqual(re_replace_literals(r, {}), o)

    def test_construct_regexp_37_change(self):
        # Starting with 3.7 the parser throws out some subpattern
        # nodes. We try to recover them or test against the old and new result.
        res = [
            ("(?:foo)", ("(?:foo)", "foo")),
            ("(?:foo)x", ("(?:foo)x", "foox")),
            ("(?:foo)(?:bar)", ("(?:foo)(?:bar)", "foobar")),
            ("(?:foo|bla)", None),
            ("(?:foo|bla)x", None),
        ]

        for r, o in res:
            out = re_replace_literals(r, {})
            if o is None:
                o = r
            if isinstance(o, tuple):
                assert out in o
            else:
                assert out == o

    def test_construct_regexp_broken(self):
        self.assertRaises(re.error, re_replace_literals, "[", {})
        self.assertRaises(
            NotImplementedError,
            re_replace_literals,
            "(?P<quote>['\"]).*?(?P=quote)",
            {},
        )

    def test_seq(self):
        assert re_add_variants("[x-y]") == "[ẋẍýÿŷȳẏẙỳỵỷỹx-y]"
        assert re_add_variants("[f-gm]") == "[ḟꝼĝğġģǧǵḡᵹf-gmḿṁṃ]"
        assert re_add_variants("[^m]") == "[^mḿṁṃ]"
        assert re_add_variants("[^m-m\\w]") == "[^ḿṁṃm-m\\w]"
        assert re_add_variants("[^m-m]") == "[^ḿṁṃm-m]"
        assert re_add_variants("[^ö]") == "[^ö]"
        assert re_add_variants("[LLL]") == "[LĹĻĽḶḸḺḼŁ]"

    def test_literal(self):
        assert re_add_variants("f") == "[fḟꝼ]"
        assert "ø" in re_add_variants("o")
        assert "Ø" in re_add_variants("O")
        assert re_add_variants("[^f]") == "[^fḟꝼ]"


class TCompileMatch(TestCase):
    def test_basics_default(self):
        assert compile("foo")("foo")
        assert compile("foo")("fooo")
        assert not compile("foo")("fo")

    def test_ignore_case(self):
        assert compile("foo", ignore_case=True)("Foo")
        assert not compile("foo", ignore_case=False)("Foo")

    def test_assert_dot_all(self):
        assert compile("a.b", dot_all=True)("a\nb")
        assert not compile("a.b", dot_all=False)("a\nb")
        assert compile("a.b", dot_all=False)("a b")

    def test_unicode_equivalence(self):
        assert compile("\u212b")("\u00c5")
        assert compile("\u00c5")("\u212b")
        assert compile("A\u030a")("\u00c5")
        assert compile("A\u030a")("\u212b")
        assert compile("o\u0308")("o\u0308")
        assert compile("o\u0308")("\xf6")
        assert compile("\xf6")("o\u0308")

    def test_assert_asym(self):
        assert compile("o", asym=True)("ö")
        assert not compile("o", asym=False)("ö")

    def test_assert_asym_unicode_equivalence(self):
        assert compile("A", asym=True)("\u00c5")
        assert compile("A\u030a", asym=True)("\u212b")
        assert compile("\u00c5", asym=True)("\u212b")
        assert compile("\u212b", asym=True)("\u00c5")

    def test_invalid(self):
        with self.assertRaises(ValueError):
            compile("(F", asym=False)

        with self.assertRaises(ValueError):
            compile("(F", asym=True)
