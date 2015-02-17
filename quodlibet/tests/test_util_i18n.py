# -*- coding: utf-8 -*-
from tests import TestCase

from quodlibet.util.i18n import GlibTranslations


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
