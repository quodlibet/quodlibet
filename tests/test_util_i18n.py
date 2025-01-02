# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import contextlib
import os

from tests import TestCase
from .helper import preserve_environ, locale_numeric_conv

from quodlibet.util import i18n
from quodlibet.util.i18n import (
    GlibTranslations,
    bcp47_to_language,
    set_i18n_envvars,
    fixup_i18n_envvars,
    osx_locale_id_to_lang,
    numeric_phrase,
    get_available_languages,
    iter_locale_dirs,
)


@contextlib.contextmanager
def use_dummy_ngettext(exp_singular, exp_plural, ret_singular, ret_plural):
    """Replace ngettext with a dummy implementation that returns
    predefined translations if given source text equals expected value
    and otherwise the source text unchanged.
    """

    original_ngettext = i18n.ngettext
    try:

        def dummy_ngettext(singular, plural, n):
            if n == 1 and singular == exp_singular:
                return ret_singular
            elif n != 1 and plural == exp_plural:
                return ret_plural
            else:
                return singular if n == 1 else plural

        i18n.ngettext = dummy_ngettext
        yield
    finally:
        i18n.ngettext = original_ngettext


class TGlibTranslations(TestCase):
    def setUp(self):
        self.t = GlibTranslations()

    def test_ugettext(self):
        t = self.t.ugettext("foo")
        self.assertEqual(t, "foo")
        assert isinstance(t, str)

    def test_ungettext(self):
        t = self.t.ungettext("foo", "bar", 1)
        self.assertEqual(t, "foo")
        assert isinstance(t, str)

        t = self.t.ungettext("foo", "bar", 2)
        self.assertEqual(t, "bar")
        assert isinstance(t, str)

    def test_upgettext(self):
        t = self.t.upgettext("ctx", "foo")
        self.assertEqual(t, "foo")
        assert isinstance(t, str)

    def test_unpgettext(self):
        t = self.t.unpgettext("ctx", "foo", "bar", 1)
        self.assertEqual(t, "foo")
        assert isinstance(t, str)

        t = self.t.unpgettext("ctx", "foo", "bar", 2)
        self.assertEqual(t, "bar")
        assert isinstance(t, str)


class Tgettext(TestCase):
    def test_iter_locale_dirs(self):
        for dir_ in iter_locale_dirs():
            assert isinstance(dir_, str)

        dirs = list(iter_locale_dirs())
        assert len(dirs) == len(set(dirs))

    def test_get_languages(self):
        assert isinstance(get_available_languages("quodlibet"), set)
        assert isinstance(get_available_languages("quodlibet_nope"), set)

    def test_bcp47(self):
        self.assertEqual(bcp47_to_language("zh-Hans"), "zh_CN")
        self.assertEqual(bcp47_to_language("pt-PT"), "pt_PT")
        self.assertEqual(bcp47_to_language("de"), "de")

        # ignore script
        self.assertEqual(bcp47_to_language("sr-Latn-CS"), "sr_CS")

        # unsupported, support something at least
        self.assertEqual(bcp47_to_language("zh-guoyu"), "zh")

    def test_set_envvars(self):
        with preserve_environ():
            set_i18n_envvars()

    def test_osx_locale_id_to_lang(self):
        self.assertEqual(osx_locale_id_to_lang("de_DE"), "de_DE")
        self.assertEqual(osx_locale_id_to_lang("zh-Hans_TW"), "zh_TW")
        self.assertEqual(osx_locale_id_to_lang("zh-foo-bar_AT"), "zh_AT")

    def test_fixup_i18n_envvars(self):
        with preserve_environ():
            os.environ["LANGUAGE"] = "en:de:en_FOO:nl"
            fixup_i18n_envvars()
            self.assertEqual(os.environ["LANGUAGE"], "en:C:de:en_FOO:C:nl")

    def test_numeric_phrase(self):
        actual = numeric_phrase("%d green bottle", "%d green bottles", 1)
        self.assertEqual(actual, "1 green bottle")

        with locale_numeric_conv():
            actual = numeric_phrase("%d green bottle", "%d green bottles", 1234)
            self.assertEqual(actual, "1,234 green bottles")

    def test_numeric_phrase_locales(self):
        with locale_numeric_conv(thousands_sep=" "):
            actual = numeric_phrase(
                "%(bottles)d green bottle", "%(bottles)d green bottles", 1234, "bottles"
            )
            self.assertEqual(actual, "1 234 green bottles")

    def test_numeric_phrase_templated(self):
        actual = numeric_phrase(
            "%(bottles)d green bottle", "%(bottles)d green bottles", 1, "bottles"
        )
        self.assertEqual(actual, "1 green bottle")

        with locale_numeric_conv():
            actual = numeric_phrase(
                "%(bottles)d green bottle", "%(bottles)d green bottles", 1234, "bottles"
            )

            self.assertEqual(actual, "1,234 green bottles")

    def test_numeric_phrase_translation(self):
        # See issue 2166

        with use_dummy_ngettext(
            "%d text", "%d texts", "%d translation", "%d translations"
        ):
            actual = numeric_phrase("%d text", "%d texts", 1)
            self.assertEqual(actual, "1 translation")

            actual = numeric_phrase("%d text", "%d texts", 2)
            self.assertEqual(actual, "2 translations")

    def test_numeric_phrase_translation_templated(self):
        # See issue 2166

        with use_dummy_ngettext(
            "%(n)d text", "%(n)d texts", "%(n)d translation", "%(n)d translations"
        ):
            actual = numeric_phrase("%(n)d text", "%(n)d texts", 1, "n")
            self.assertEqual(actual, "1 translation")

            actual = numeric_phrase("%(n)d text", "%(n)d texts", 2, "n")
            self.assertEqual(actual, "2 translations")
