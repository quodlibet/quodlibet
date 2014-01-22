# Copyright 2012,2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from tests import TestCase
from quodlibet import config
from quodlibet.qltk.ratingsmenu import RatingsMenuItem
from quodlibet.library import SongLibrary, SongLibrarian
from quodlibet.formats._audio import AudioFile


class TRatingsMenuItem(TestCase):

    def setUp(self):
        config.init()

    def tearDown(self):
        config.quit()

    def test_menuitem(self):
        library = SongLibrary()
        library.librarian = SongLibrarian()
        a = AudioFile({"~filename": "/foo"})
        a.sanitize()
        x = RatingsMenuItem([a], library)
        x.set_rating(0, [a], library)
        x.destroy()
        library.destroy()
        library.librarian.destroy()
