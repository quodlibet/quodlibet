# -*- coding: utf-8 -*-
# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from gi.repository import Gtk

from tests import TestCase
from .helper import realized

from quodlibet.qltk.util import position_window_beside_widget


class Tposition_window_beside_widget(TestCase):

    def test_main(self):
        button = Gtk.Button()
        window = Gtk.Window()
        with realized(button):
            position_window_beside_widget(window, button, True)
            position_window_beside_widget(window, button, False)
