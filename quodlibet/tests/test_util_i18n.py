# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
import locale
import os
import contextlib

from tests import TestCase, skipIf
from .helper import preserve_environ

from quodlibet.util.i18n import GlibTranslations, bcp47_to_language, \
    set_i18n_envvars, fixup_i18n_envvars, osx_locale_id_to_lang, numeric_phrase
from quodlibet.util import is_osx
from quodlibet.compat import text_type


class TGlibTranslations(TestCase):

    def setUp(self):
        self.t = GlibTranslations()

    def test_ugettext(self):
        t = self.t.ugettext("foo")
        self.assertEqual(t, "foo")
        self.assertTrue(isinstance(t, text_type))

    def test_ungettext(self):
        t = self.t.ungettext("foo", "bar", 1)
        self.assertEqual(t, "foo")
        self.assertTrue(isinstance(t, text_type))

        t = self.t.ungettext("foo", "bar", 2)
        self.assertEqual(t, "bar")
        self.assertTrue(isinstance(t, text_type))

    def test_upgettext(self):
        t = self.t.upgettext("ctx", "foo")
        self.assertEqual(t, "foo")
        self.assertTrue(isinstance(t, text_type))

    def test_unpgettext(self):
        t = self.t.unpgettext("ctx", "foo", "bar", 1)
        self.assertEqual(t, "foo")
        self.assertTrue(isinstance(t, text_type))

        t = self.t.unpgettext("ctx", "foo", "bar", 2)
        self.assertEqual(t, "bar")
        self.assertTrue(isinstance(t, text_type))


def has_locale(loc):
    if is_osx():
        return False

    try:
        with set_locale(loc):
            pass
    except locale.Error:
        return False
    else:
        return True


@contextlib.contextmanager
def set_locale(loc):
    """
    with set_locale('fr_FR.utf-8'):
        do_something()

    Raises:
        locale.Error
    """

    old_loc = locale.setlocale(locale.LC_ALL)
    locale.setlocale(locale.LC_ALL, loc)
    try:
        yield
    finally:
        locale.setlocale(locale.LC_ALL, old_loc)


class Tgettext(TestCase):

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
        self.failUnlessEqual(actual, "1 green bottle")

        actual = numeric_phrase("%d green bottle", "%d green bottles", 1234)
        self.failUnlessEqual(actual, "1,234 green bottles")

    @skipIf(not has_locale('fr_FR.utf-8'), "locale missing")
    def test_numeric_phrase_locales(self):
        with set_locale('fr_FR.utf-8'):
            actual = numeric_phrase("%(bottles)d green bottle",
                                    "%(bottles)d green bottles",
                                    1234, "bottles")
            self.failUnlessEqual(actual, "1 234 green bottles")

    def test_numeric_phrase_templated(self):
        actual = numeric_phrase("%(bottles)d green bottle",
                                "%(bottles)d green bottles", 1, "bottles")
        self.failUnlessEqual(actual, "1 green bottle")

        actual = numeric_phrase("%(bottles)d green bottle",
                                "%(bottles)d green bottles", 1234, "bottles")

        self.failUnlessEqual(actual, "1,234 green bottles")
