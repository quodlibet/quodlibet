# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import config
from quodlibet.browsers.tracks import TrackList
from quodlibet.formats import AudioFile
from quodlibet.library import SongFileLibrary, SongLibrarian
from quodlibet.qltk.songlist import (SongList, set_columns, get_columns,
                                     header_tag_split, get_sort_tag)
from quodlibet.qltk.songlistcolumns import SongListColumn
from senf import fsnative
from tests import TestCase, run_gtk_loop


class TSongList(TestCase):
    HEADERS = ["acolumn", "~#lastplayed", "~foo~bar", "~#rating",
               "~#length", "~dirname", "~#track"]

    def setUp(self):
        config.init()
        self.lib = SongFileLibrary()
        self.songlist = SongList(self.lib)
        assert not self.lib.librarian, "not expecting a librarian - leaky test?"

        self.orders_changed = 0
        self.songs_removed: list[set] = []

        def orders_changed_cb(*args):
            self.orders_changed += 1

        def orders_removed_cb(songlist, removed):
            self.songs_removed.append(removed)

        self.__sigs = [
            self.songlist.connect("orders-changed", orders_changed_cb),
            self.songlist.connect("songs-removed", orders_removed_cb)
        ]

    def test_set_all_column_headers(self):
        SongList.set_all_column_headers(self.HEADERS)
        headers = [col.header_name for col in self.songlist.get_columns()]
        self.assertEqual(headers, self.HEADERS)

    def test_set_column_headers(self):
        self.songlist.set_column_headers(self.HEADERS)
        headers = [col.header_name for col in self.songlist.get_columns()]
        self.assertEqual(headers, self.HEADERS)

    def test_drop(self):
        self.songlist.enable_drop()
        self.songlist.disable_drop()

    def test_sort_by(self):
        self.songlist.set_column_headers(["one", "two", "three"])
        for key, order in [("one", True),
                           ("two", False),
                           ("three", False)]:
            self.songlist.set_sort_orders([(key, order)])
            self.assertEqual(
                self.songlist.get_sort_orders(), [(key, order)])

        self.songlist.toggle_column_sort(self.songlist.get_columns()[-1])
        self.assertEqual(
            self.songlist.get_sort_orders(), [("three", True)])

    def test_sort_orders(self):
        s = self.songlist

        s.set_column_headers(["foo", "quux", "bar"])
        values = [("foo", True), ("bar", False)]
        s.set_sort_orders(values)
        self.assertEqual(s.get_sort_orders(), values)

        s.toggle_column_sort(s.get_columns()[1], replace=False)
        self.assertEqual(s.get_sort_orders(), values + [("quux", False)])

        s.toggle_column_sort(s.get_columns()[1], replace=True)
        self.assertEqual(s.get_sort_orders(), [("quux", False)])

    def test_toggle_sort(self):
        s = self.songlist

        s.set_column_headers(["foo"])
        self.assertEqual(self.orders_changed, 1)
        s.toggle_column_sort(s.get_columns()[0], replace=True)
        self.assertEqual(self.orders_changed, 2)
        self.assertEqual(s.get_sort_orders(), [("foo", False)])
        s.toggle_column_sort(s.get_columns()[0], replace=True)
        self.assertEqual(self.orders_changed, 3)
        self.assertEqual(s.get_sort_orders(), [("foo", True)])

    def test_clear_sort(self):
        s = self.songlist
        s.set_column_headers(["foo"])
        s.toggle_column_sort(s.get_columns()[0], replace=True)
        self.assertTrue(s.get_sort_orders())
        s.clear_sort()
        self.assertFalse(s.get_sort_orders())

    def test_not_sortable(self):
        config.set("song_list", "always_allow_sorting", False)
        s = self.songlist
        s.sortable = False

        s.set_column_headers(["foo"])
        s.toggle_column_sort(s.get_columns()[0])
        assert self.orders_changed == 0
        assert not s.get_sort_orders()


    def test_sortable_if_config_overrides(self):
        config.set("song_list", "always_allow_sorting", True)
        s = self.songlist
        s.sortable = False
        assert s.sortable
        s.set_column_headers(["foo"])
        s.toggle_column_sort(s.get_columns()[0])
        assert s.get_sort_orders()

    def test_find_default_sort_column(self):
        s = self.songlist
        self.assertTrue(s.find_default_sort_column() is None)
        s.set_column_headers(["~#track"])
        self.assertTrue(s.find_default_sort_column())

    def test_inline_search_state(self):
        self.assertEqual(self.songlist.get_search_column(), 0)
        self.assertTrue(self.songlist.get_enable_search())

    def test_set_songs(self):
        self.songlist.set_songs([], sorted=True)
        self.songlist.set_songs([], sorted=False)
        self.songlist.set_songs([], scroll_select=True)
        self.songlist.set_songs([], scroll_select=False)
        self.songlist.set_songs([], scroll=True)
        self.songlist.set_songs([], scroll=False)

    def test_set_songs_restore_select(self):
        song = AudioFile({"~filename": "/dev/null"})
        self.songlist.add_songs([song])
        sel = self.songlist.get_selection()
        sel.select_path(Gtk.TreePath.new_first())

        self.songlist.set_songs([song], scroll_select=True)
        self.assertEqual(self.songlist.get_selected_songs(), [song])

        song2 = AudioFile({"~filename": "/dev/null"})
        self.songlist.set_songs([song2], scroll_select=True)
        self.assertEqual(self.songlist.get_selected_songs(), [])

    def test_set_songs_no_restore_select(self):
        song = AudioFile({"~filename": "/dev/null"})
        self.songlist.add_songs([song])
        model = self.songlist.get_model()
        model.go_to(song)
        self.assertIs(model.current, song)
        # only restore if there was a selected one
        self.songlist.set_songs([song], scroll_select=True)
        self.assertEqual(self.songlist.get_selected_songs(), [])

    def test_get_selected_songs(self):
        song = AudioFile({"~filename": "/dev/null"})
        self.songlist.add_songs([song])
        sel = self.songlist.get_selection()

        sel.select_path(Gtk.TreePath.new_first())
        self.assertEqual(self.songlist.get_selected_songs(), [song])
        self.assertEqual(self.songlist.get_first_selected_song(), song)

        sel.unselect_all()
        self.assertEqual(self.songlist.get_selected_songs(), [])
        self.assertIs(self.songlist.get_first_selected_song(), None)

    def test_add_songs(self):
        song = AudioFile({"~filename": "/dev/null"})

        # unsorted
        self.songlist.add_songs([song])
        self.songlist.add_songs([song])

        # sorted
        self.songlist.set_column_headers(["foo"])
        self.songlist.toggle_column_sort(self.songlist.get_columns()[0])
        self.songlist.add_songs([])
        self.songlist.add_songs([song])
        self.songlist.add_songs([song])

        self.assertEqual(self.songlist.get_songs(), [song] * 4)

    def test_remove_songs(self):
        song = AudioFile({"~filename": "/dev/null"})
        song.sanitize()
        self.lib.add([song])
        assert song in self.lib, "Broken library?"
        self.songlist.add_songs([song])
        assert set(self.songlist.get_songs()) == {song}
        self.lib.remove([song])
        assert not list(self.lib), "Didn't get removed"
        run_gtk_loop()
        assert self.songs_removed == [{song}], f"Signal not emitted: {self.__sigs}"

    def test_header_menu(self):
        song = AudioFile({"~filename": fsnative("/dev/null")})
        song.sanitize()
        self.songlist.set_songs([song])

        library = self.lib
        librarian = SongLibrarian()
        librarian.register(self.lib, "test")
        self.lib.librarian = librarian
        browser = TrackList(library)

        self.songlist.set_column_headers(["foo"])

        self.assertFalse(self.songlist.menu("foo", browser, library))
        sel = self.songlist.get_selection()
        sel.select_all()
        self.assertTrue(self.songlist.menu("foo", browser, library))
        librarian.destroy()
        self.lib.librarian = None

    def test_get_columns_migrated(self):
        self.assertFalse(config.get("settings", "headers", None))
        columns = "~album,~#replaygain_track_gain,foobar"
        config.set("settings", "columns", columns)
        self.assertEqual(get_columns(),
                             ["~album", "~#replaygain_track_gain", "foobar"])
        self.assertFalse(config.get("settings", "headers", None))

    def test_get_set_columns(self):
        self.assertFalse(config.get("settings", "headers", None))
        self.assertFalse(config.get("settings", "columns", None))
        columns = ["first", "won't", "two words", "4"]
        set_columns(columns)
        self.assertEqual(columns, get_columns())
        columns += ["~~another~one"]
        set_columns(columns)
        self.assertEqual(columns, get_columns())
        self.assertFalse(config.get("settings", "headers", None))

    def test_header_tag_split(self):
        self.assertEqual(header_tag_split("foo"), ["foo"])
        self.assertEqual(header_tag_split("~foo~bar"), ["foo", "bar"])
        self.assertEqual(header_tag_split("<foo>"), ["foo"])
        self.assertEqual(header_tag_split("<~foo~bar>"), ["foo", "bar"])
        self.assertEqual(header_tag_split("pattern <~foo~bar>"),
                         ["foo", "bar"])

    def test_get_sort_tag(self):
        self.assertEqual(get_sort_tag("~#track"), "")
        self.assertEqual(get_sort_tag("artist"), "artistsort")
        self.assertEqual(get_sort_tag("date"), "date")
        self.assertEqual(get_sort_tag("~artist~date"), "~artistsort~date")
        self.assertEqual(get_sort_tag("~date~artist"), "~date~artistsort")
        self.assertEqual(get_sort_tag("composer"), "composersort")
        self.assertEqual(get_sort_tag("originalartist"), "originalartistsort")

    def test_check_sensible_menu_items(self):
        col = SongListColumn("title")

        menu = self.songlist._menu(col)
        submenus = [item.get_submenu()
                    for item in menu.get_children()]
        names = {item.get_label()
                 for child in submenus
                 if child and not isinstance(child, Gtk.SeparatorMenuItem)
                 for item in child.get_children()}
        assert {"Title", "Genre", "Comment", "Artist"} < names

    def tearDown(self):
        for sig in self.__sigs:
            self.songlist.disconnect(sig)
        self.songlist.destroy()
        self.lib.destroy()
        config.quit()
