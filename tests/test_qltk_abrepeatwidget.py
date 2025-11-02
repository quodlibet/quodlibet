# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import unittest

from quodlibet import app
from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.abrepeatwidget import ABRepeatWidget
from quodlibet.player.nullbe import NullPlayer
from quodlibet.library.base import Library


from tests import get_data_path
from tests.helper import visible


class DummySong(AudioFile):
    def __init__(self):
        super().__init__()
        self["~filename"] = get_data_path("lame.mp3")


class TABRepeatWidget(unittest.TestCase):
    def setUp(self):
        self.library = Library()
        self.player = NullPlayer(librarian=self.library)
        app.player = self.player
        self.widget = ABRepeatWidget()
        self.song = DummySong()
        self.player.song = self.song

    def tearDown(self):
        self.widget.destroy()
        self.player.song = None
        app.player = None

    def test_initial_state(self):
        with visible(self.widget):
            self.assertFalse(self.widget._button_a.get_active())
            self.assertFalse(self.widget._button_b.get_active())

    def test_set_a_point(self):
        with visible(self.widget):
            self.player.seek(1000)
            self.widget._button_a.set_active(True)
        self.assertEqual(self.player.get_ab_points(), (1, None))

    def test_set_b_point(self):
        with visible(self.widget):
            self.player.seek(2000)
            self.widget._button_b.set_active(True)
        self.assertEqual(self.player.get_ab_points(), (None, 2))

    def test_clear_a_point(self):
        with visible(self.widget):
            self.player.set_ab_points(1, 10)
        with visible(self.widget):
            self.assertTrue(self.widget._button_a.get_active())
            self.widget._button_a.set_active(False)
        self.assertEqual(self.player.get_ab_points(), (None, 10))

    def test_clear_b_point(self):
        with visible(self.widget):
            self.player.set_ab_points(1, 10)
        with visible(self.widget):
            self.assertTrue(self.widget._button_b.get_active())
            self.widget._button_b.set_active(False)
        self.assertEqual(self.player.get_ab_points(), (1, None))

    def test_clear_all_points(self):
        with visible(self.widget):
            self.player.set_ab_points(5, 15)
        with visible(self.widget):
            self.assertTrue(self.widget._button_a.get_active())
            self.widget._on_clear_clicked()
        self.assertEqual(self.player.get_ab_points(), (None, None))
        self.assertFalse(self.widget._button_a.get_active())

    def test_ab_points_cleared_on_new_song(self):
        with visible(self.widget):
            self.player.seek(1000)
            self.widget._button_a.set_active(True)
        self.assertEqual(self.player.get_ab_points(), (1, None))

        with visible(self.widget):
            new_song = DummySong()
            self.player.song = new_song
        self.assertEqual(self.player.get_ab_points(), (None, None))

    def test_ab_points_per_song(self):
        song1 = self.song
        with visible(self.widget):
            self.player.seek(1000)
            self.widget._button_a.set_active(True)
        self.assertEqual(self.player.get_ab_points(), (1, None))

        song2 = DummySong()
        self.player.song = song2
        with visible(self.widget):
            self.player.seek(5000)
            self.widget._button_b.set_active(True)
        self.assertEqual(self.player.get_ab_points(), (None, 5))

        self.player.song = song1
        with visible(self.widget):
            pass
        self.assertEqual(self.player.get_ab_points(), (1, None))

        self.player.song = song2
        with visible(self.widget):
            pass
        self.assertEqual(self.player.get_ab_points(), (None, 5))

    def test_song_changed_updates_state(self):
        with visible(self.widget):
            self.player.set_ab_points(1, 10)
        with visible(self.widget):
            self.assertTrue(self.widget._button_a.get_active())
            self.player.set_ab_points(None, None)
            self.player.song = DummySong()
        self.assertFalse(self.widget._button_a.get_active())

    def test_song_started_updates_state(self):
        with visible(self.widget):
            self.player.set_ab_points(1, 10)
        with visible(self.widget):
            self.assertTrue(self.widget._button_a.get_active())
            self.player.set_ab_points(None, None)
            self.player.emit("song-started", self.song)
        self.assertFalse(self.widget._button_a.get_active())
