# -*- coding: utf-8 -*-
import os

from tests import TestCase
from .helper import preserve_environ

from quodlibet.util.i18n import GlibTranslations, bcp47_to_language, \
    set_i18n_envvars, fixup_i18n_envvars, osx_locale_id_to_lang


class TGlibTranslations(TestCase):

    def setUp(self):
        self.t = GlibTranslations()

    def test_ugettext(self):
        t = self.t.ugettext("foo")
        self.assertEqual(t, "foo")
        self.assertTrue(isinstance(t, unicode))

    def test_ungettext(self):
        t = self.t.ungettext("foo", "bar", 1)
        self.assertEqual(t, "foo")
        self.assertTrue(isinstance(t, unicode))

        t = self.t.ungettext("foo", "bar", 2)
        self.assertEqual(t, "bar")
        self.assertTrue(isinstance(t, unicode))

    def test_upgettext(self):
        t = self.t.upgettext("ctx", "foo")
        self.assertEqual(t, "foo")
        self.assertTrue(isinstance(t, unicode))

    def test_unpgettext(self):
        t = self.t.unpgettext("ctx", "foo", "bar", 1)
        self.assertEqual(t, "foo")
        self.assertTrue(isinstance(t, unicode))

        t = self.t.unpgettext("ctx", "foo", "bar", 2)
        self.assertEqual(t, "bar")
        self.assertTrue(isinstance(t, unicode))


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
