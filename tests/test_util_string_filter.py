# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase

from quodlibet.util.string.filter import remove_diacritics, remove_punctuation

SOME_FRENCH = "goût d'œufs à Noël"


class TRemoveDiacritics(TestCase):

    def test_empty(self):
        assert remove_diacritics("") == ""
        assert remove_diacritics(" \t\n") == " \t\n"

    def test_harder(self):
        assert remove_diacritics("abc '123' ?!") == "abc '123' ?!"
        assert remove_diacritics(SOME_FRENCH) == "gout d'œufs a Noel"


class TRemovePunctuation(TestCase):

    def test_empty(self):
        assert remove_punctuation("") == ""
        assert remove_punctuation(" \t\n") == " \t\n"

    def test_harder(self):
        assert remove_punctuation("\"abc\" '123' ?!") == "abc 123 "
        assert remove_punctuation(SOME_FRENCH) == "goût dœufs à Noël"

    def test_unicode(self):
        assert remove_punctuation("†one⁋two\u2003three") == "onetwo\u2003three"
