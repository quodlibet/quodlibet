# Copyright 2011, 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from . import add_css


class MenuButton(Gtk.MenuButton):
    """TODO: remove. This used to be an implementation of Gtk.MenuButton
    when it wasn't available in gtk+
    """

    def __init__(self, widget=None, arrow=False, down=True):
        super().__init__()

        bbox = Gtk.HBox(spacing=3)
        if widget:
            bbox.pack_start(widget, True, True, 0)
        if arrow:
            arrow_type = Gtk.ArrowType.DOWN if down else Gtk.ArrowType.UP
            bbox.pack_start(Gtk.Arrow.new(arrow_type, Gtk.ShadowType.IN), True, True, 0)

        self.add(bbox)
        self.set_direction(Gtk.ArrowType.DOWN if down else Gtk.ArrowType.UP)

    def get_menu(self):
        return self.get_popup()

    def set_menu(self, menu):
        self.set_popup(menu)


class SmallMenuButton(MenuButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_size_request(26, 26)
        add_css(
            self,
            """
            * {
                padding: 0px 4px;
            }
        """,
        )
