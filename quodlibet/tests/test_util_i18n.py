# -*- coding: utf-8 -*-
import os

from tests import TestCase

from quodlibet.util.i18n import GlibTranslations, bcp47_to_language, \
    set_i18n_envvars


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
        old = os.environ.copy()
        try:
            set_i18n_envvars()
        finally:
            os.environ.clear()
            os.environ.update(old)
