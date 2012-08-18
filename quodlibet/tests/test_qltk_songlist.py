from tests import TestCase, add

import gtk

from quodlibet.library import SongLibrary
from quodlibet.qltk.songlist import SongList
import quodlibet.config


class TSongList(TestCase):
    HEADERS = ["acolumn", "~#lastplayed", "~foo~bar", "~#rating",
               "~#length", "~dirname", "~#track"]
    def setUp(self):
        quodlibet.config.init()
        self.songlist = SongList(SongLibrary())

    def test_set_all_column_headers(self):
        SongList.set_all_column_headers(self.HEADERS)
        headers = [col.header_name for col in self.songlist.get_columns()]
        self.failUnlessEqual(headers, self.HEADERS)

    def test_set_column_headers(self):
        self.songlist.set_column_headers(self.HEADERS)
        headers = [col.header_name for col in self.songlist.get_columns()]
        self.failUnlessEqual(headers, self.HEADERS)

    def test_drop(self):
        self.songlist.enable_drop()
        self.songlist.disable_drop()

    def test_sort_by(self):
        self.songlist.set_column_headers(["one", "two", "three"])
        for key, order in [("one", True),
                           ("two", False),
                           ("three", False)]:
            self.songlist.set_sort_by(None, tag=key, order=order)
            self.failUnlessEqual(self.songlist.get_sort_by(), (key, order))
        self.songlist.set_sort_by(self.songlist.get_columns()[-1], tag="three")
        self.failUnlessEqual(self.songlist.get_sort_by(), ("three", True))

    def tearDown(self):
        self.songlist.destroy()
        quodlibet.config.quit()
add(TSongList)
