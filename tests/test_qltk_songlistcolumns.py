# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase
from .helper import visible

from gi.repository import Gtk
from senf import devnull

from quodlibet.qltk.songlistcolumns import create_songlist_column
from quodlibet.qltk.songmodel import PlaylistModel
from quodlibet.formats import AudioFile
import quodlibet.config

import datetime
import time


class TSongListColumns(TestCase):
    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()

    def _render_column(self, column, **kwargs):
        view = Gtk.TreeView()
        model = PlaylistModel()
        view.set_model(model)
        song = AudioFile({"~filename": devnull, "~#rating": 0.6666})
        song.update(kwargs)
        model.append(row=[song])
        view.append_column(column)
        if column.get_resizable():
            column.set_expand(True)

        with visible(view):
            view.columns_autosize()

        text = column.get_cells()[0].get_property("text")
        self.assertIsNot(text, None)
        return text

    def test_date(self):
        column = create_songlist_column("~#added")
        self._render_column(column)

        # column reuse triggers warning somwhow
        column = create_songlist_column("~#added")
        self._render_column(column, **{"~#added": 100})

    def test_length(self):
        column = create_songlist_column("~length")
        self._render_column(column)

    def test_filesize(self):
        column = create_songlist_column("~#filesize")
        self._render_column(column)

    def test_rating(self):
        column = create_songlist_column("~rating")
        text = self._render_column(column)
        self.assertNotEqual(text, "0.67")

        column = create_songlist_column("~#rating")
        text = self._render_column(column)
        self.assertEqual(text, "0.67")

    def test_bitrate(self):
        column = create_songlist_column("~#bitrate")
        self._render_column(column)

    def test_basename(self):
        column = create_songlist_column("~basename")
        self._render_column(column)

    def test_pattern(self):
        column = create_songlist_column("<artist>-<album>")
        self._render_column(column)

    def test_artist(self):
        column = create_songlist_column("artist")
        self._render_column(column)

    def test_people(self):
        column = create_songlist_column("~people")
        self._render_column(column)

    def test_bpm(self):
        column = create_songlist_column("bpm")
        text = self._render_column(column, **{"bpm": "123"})
        self.assertEqual(text, "123")

    def test_custom_datecol_format(self):
        format = "%Y%m%d %H:%M:%S PLAINTEXT"
        quodlibet.config.settext("settings", "datecolumn_timestamp_format",
                                 format)

        d = datetime.datetime(year=1999, month=5, day=1,
                              hour=23, minute=11, second=59)
        stamp = int(time.mktime(d.timetuple()))
        column = create_songlist_column("~#added")
        text = self._render_column(column, **{"~#added": stamp})
        self.assertEqual(text, "19990501 23:11:59 PLAINTEXT")

    def test_nonconfigured_datecol_format(self):
        # make sure config option is unset by default
        text = quodlibet.config.gettext("settings",
                                        "datecolumn_timestamp_format")
        self.assertEqual(text, "")

        # make sure unset config option does not result in the
        # behaviour for testcase for set option above
        d = datetime.datetime(year=1999, month=5, day=1,
                              hour=23, minute=11, second=59)
        stamp = int(time.mktime(d.timetuple()))
        column = create_songlist_column("~#added")
        text = self._render_column(column, **{"~#added": stamp})
        self.assertNotEqual(text, "19990501 23:11:59 PLAINTEXT")
