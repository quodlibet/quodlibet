# -*- coding: utf-8 -*-
# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from tests import TestCase
import quodlibet


class TIconTheme(TestCase):
    def test_icon_theme(self):
        theme = Gtk.IconTheme.get_default()
        theme.append_search_path(quodlibet.get_image_dir())

        for i in ["quodlibet", "exfalso", "quodlibet-missing-cover"]:
            self.failUnless(theme.has_icon(i))
