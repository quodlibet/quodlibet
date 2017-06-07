# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from tests import TestCase

from quodlibet.qltk.seekbutton import HSlider, SeekButton, TimeLabel
from quodlibet.library import SongLibrary
from quodlibet.player.nullbe import NullPlayer


class TSlider(TestCase):

    def test_basics(self):
        s = HSlider()
        s.set_slider_disabled(True)
        s.set_slider_disabled(False)
        s.set_slider_length(100)
        s.set_slider_widget(Gtk.Button())
        s.destroy()


class TTimeLabel(TestCase):

    def test_time_label(self):
        l = TimeLabel()
        l.set_time(42)
        time_text = l.get_text()
        l.set_disabled(True)
        disabled_text = l.get_text()
        self.assertNotEqual(time_text, disabled_text)
        l.set_disabled(False)
        self.assertEqual(l.get_text(), time_text)


class TSeekButton(TestCase):

    def test_seekbutton(self):
        w = SeekButton(NullPlayer(), SongLibrary())
        w.destroy()
