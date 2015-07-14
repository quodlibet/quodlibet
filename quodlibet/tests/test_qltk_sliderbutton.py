# -*- coding: utf-8 -*-
# Copyright 2015 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from tests import TestCase

from quodlibet.qltk.sliderbutton import HSlider


class TSlider(TestCase):

    def test_basics(self):
        s = HSlider()
        s.set_slider_disabled(True)
        s.set_slider_disabled(False)
        s.set_slider_length(100)
        s.set_slider_widget(Gtk.Button())
        s.destroy()
