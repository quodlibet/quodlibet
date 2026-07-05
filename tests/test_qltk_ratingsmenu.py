# Copyright 2012,2013 Christoph Reiter
#                2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gio

from tests import TestCase
from quodlibet import config
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.library import SongLibrary, SongLibrarian
from quodlibet.formats import AudioFile

NUM_RATINGS = 4


class TRatingsMenuItem(TestCase):
    def setUp(self):
        config.RATINGS = config.HardCodedRatingsPrefs()
        self.assertEqual(config.RATINGS.number, NUM_RATINGS)
        self.library = SongLibrary()
        self.library.librarian = SongLibrarian()
        self.af = AudioFile({"~filename": "/foo", "~#rating": 1.0})
        self.af.sanitize()
        self.actions = Gio.SimpleActionGroup()
        self.rmi = RatingsMenuItem([self.af], self.library, self.actions, "songs")

    def tearDown(self):
        self.library.destroy()
        self.library.librarian.destroy()

    def _rating_state(self):
        return self.actions.lookup_action("rating").get_state().get_double()

    def test_submenu_structure(self):
        submenu = self.rmi.submenu
        self.assertEqual(submenu.get_n_items(), 2)
        ratings = submenu.get_item_link(0, Gio.MENU_LINK_SECTION)
        self.assertEqual(ratings.get_n_items(), NUM_RATINGS + 1)

    def test_state_reflects_common_rating(self):
        # af is rated the maximum (1.0), so that value should be selected
        self.assertEqual(self._rating_state(), 1.0)

    def test_no_rating(self):
        af = AudioFile({"~filename": "/foobar", "artist": "foo"})
        actions = Gio.SimpleActionGroup()
        RatingsMenuItem([af], self.library, actions, "songs")
        self.assertEqual(actions.lookup_action("rating").get_state().get_double(), -1.0)

    def test_set_remove_rating(self):
        self.rmi.set_rating(0.5, [self.af], self.library)
        assert self.af.has_rating
        self.assertEqual(self.af("~#rating"), 0.5)
        self.rmi.remove_rating([self.af], self.library)
        assert not self.af.has_rating
