# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.query import Query

from . import TestCase


class TSearchBarBox(TestCase):

    def test_get_query(self):
        sbb = SearchBarBox()
        self.failIf(sbb.get_query(None))
        a_star = ["artist", "date", "custom"]
        sbb.set_text("foobar")
        expected = Query("foobar", star=a_star)
        self.failUnlessEqual(sbb.get_query(a_star), expected)

    def test_get_query_override_star(self):
        sbb = SearchBarBox(star=["initial"])
        text = "foobar"
        sbb.set_text(text)
        self.failUnlessEqual(sbb.get_query(), Query(text, star=["initial"]))
        another_star = ["another", "star"]
        self.failUnlessEqual(sbb.get_query(star=another_star),
                             Query(text, star=another_star))
