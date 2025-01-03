# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from tests import TestCase
from .helper import visible

from gi.repository import Gtk

from quodlibet.qltk.songlistcolumns import create_songlist_column
from quodlibet.qltk.songmodel import PlaylistModel
from quodlibet.formats import AudioFile
import quodlibet.config

import datetime
import time

A_DATETIME = datetime.datetime(year=1999, month=5, day=1, hour=23, minute=11, second=59)


class TSongListColumns(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.model = object()

    def tearDown(self):
        quodlibet.config.quit()

    def _create_col(self, t):
        return create_songlist_column(self.model, t)

    def _render_column(self, column, **kwargs):
        view = Gtk.TreeView()
        model = PlaylistModel()
        view.set_model(model)
        song = AudioFile({"~filename": os.devnull, "~#rating": 0.6666})
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
        column = self._create_col("~#added")
        self._render_column(column)

        # column reuse triggers warning somwhow
        column = self._create_col("~#added")
        self._render_column(column, **{"~#added": 100})

    def test_length(self):
        column = self._create_col("~length")
        self._render_column(column)

    def test_filesize(self):
        column = self._create_col("~#filesize")
        self._render_column(column)

    def test_rating(self):
        column = self._create_col("~rating")
        text = self._render_column(column)
        self.assertNotEqual(text, "0.67")

        column = self._create_col("~#rating")
        text = self._render_column(column)
        self.assertEqual(text, "0.67")

    def test_bitrate(self):
        column = self._create_col("~#bitrate")
        self._render_column(column)

    def test_basename(self):
        column = self._create_col("~basename")
        self._render_column(column)

    def test_pattern(self):
        column = self._create_col("<artist>-<album>")
        self._render_column(column)

    def test_artist(self):
        column = self._create_col("artist")
        self._render_column(column)

    def test_people(self):
        column = self._create_col("~people")
        self._render_column(column)

    def test_bpm(self):
        column = self._create_col("bpm")
        text = self._render_column(column, **{"bpm": "123"})
        self.assertEqual(text, "123")

    def test_initialkey(self):
        column = self._create_col("initialkey")
        text = self._render_column(column, **{"initialkey": "F"})
        self.assertEqual(text, "F")

    def test_custom_datecol_format(self):
        format = "%Y%m%d %H:%M:%S PLAINTEXT"
        quodlibet.config.settext("settings", "datecolumn_timestamp_format", format)

        stamp = int(time.mktime(A_DATETIME.timetuple()))
        column = self._create_col("~#added")
        text = self._render_column(column, **{"~#added": stamp})
        self.assertEqual(text, "19990501 23:11:59 PLAINTEXT")

    def test_nonconfigured_datecol_format(self):
        # make sure config option is unset by default
        text = quodlibet.config.gettext("settings", "datecolumn_timestamp_format")
        self.assertEqual(text, "")

        # make sure unset config option does not result in the
        # behaviour for testcase for set option above
        stamp = int(time.mktime(A_DATETIME.timetuple()))
        column = self._create_col("~#added")
        text = self._render_column(column, **{"~#added": stamp})
        self.assertNotEqual(text, "19990501 23:11:59 PLAINTEXT")
