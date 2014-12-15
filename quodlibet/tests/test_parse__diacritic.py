# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase

from quodlibet.parse._diacritic import re_add_diacritics, diacritic_for_letters


class TDiacritics(TestCase):

    def test_mapping(self):
        cache = diacritic_for_letters(False)
        new = diacritic_for_letters(True)
        self.assertEqual(sorted(cache.items()), sorted(new.items()))

    def test_re_replace(self):
        r = re_add_diacritics(u"aa")
        self.assertTrue(u"[" in r and u"]" in r and r.count(u"ä") == 2)
        print re_add_diacritics(u"Mum")
