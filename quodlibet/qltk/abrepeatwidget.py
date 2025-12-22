# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GObject

from quodlibet import _
from quodlibet import app
from quodlibet import qltk
from quodlibet.qltk import Icons
from quodlibet.qltk.x import MenuItem, HighlightToggleButton
from quodlibet.qltk.menubutton import MenuButton
from quodlibet.util import connect_destroy


class ABRepeatWidget(Gtk.HBox):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self):
        super().__init__(spacing=0)
        self.set_name("ql-abrepeat-widget")

        context = self.get_style_context()
        context.add_class(Gtk.STYLE_CLASS_LINKED)

        self._button_a = HighlightToggleButton("A")
        self._button_a.set_size_request(26, 26)
        self._button_a.set_tooltip_text(_("Set A point"))
        qltk.remove_padding(self._button_a)
        self._button_a_handler = self._button_a.connect(
            "toggled", self._on_button_a_toggled
        )
        self.pack_start(self._button_a, False, False, 0)

        self._button_b = HighlightToggleButton("B")
        self._button_b.set_size_request(26, 26)
        self._button_b.set_tooltip_text(_("Set B point"))
        qltk.remove_padding(self._button_b)
        self._button_b_handler = self._button_b.connect(
            "toggled", self._on_button_b_toggled
        )
        self.pack_start(self._button_b, False, False, 0)

        self._menu_button = MenuButton(arrow=True, down=False)
        self._menu_button.set_size_request(20, 26)
        qltk.remove_padding(self._menu_button)
        self.pack_start(self._menu_button, False, False, 0)

        self.__rebuild_menu()

        connect_destroy(app.player, "song-started", self._on_song_changed)
        connect_destroy(app.player, "notify::song", self._on_song_changed)
        connect_destroy(
            app.player, "ab-seek-points-changed", self._on_ab_points_changed
        )

        self.show_all()
        self._update_button_states()

    def __rebuild_menu(self):
        menu = Gtk.Menu()
        item_clear = MenuItem(_("Clear A-B Repeat"), Icons.EDIT_CLEAR)
        item_clear.connect("activate", self._on_clear_clicked)
        menu.append(item_clear)
        menu.show_all()
        self._menu_button.set_menu(menu)

    def _on_song_changed(self, player, *args):
        self._update_button_states()

    def _on_ab_points_changed(self, player, a_point, b_point):
        self._update_button_states()

    def _update_button_states(self):
        song = app.player.song
        a_point, b_point = (None, None) if not song else app.player.get_ab_points()

        self._button_a.handler_block(self._button_a_handler)
        self._button_a.set_active(a_point is not None)
        self._button_a.handler_unblock(self._button_a_handler)

        self._button_b.handler_block(self._button_b_handler)
        self._button_b.set_active(b_point is not None)
        self._button_b.handler_unblock(self._button_b_handler)

        self._menu_button.set_sensitive(a_point is not None or b_point is not None)

    def _on_button_a_toggled(self, button):
        self._set_or_clear_bookmark("A", button.get_active())

    def _on_button_b_toggled(self, button):
        self._set_or_clear_bookmark("B", button.get_active())

    def _on_clear_clicked(self, *args):
        app.player.set_ab_points(None, None)

    def _set_or_clear_bookmark(self, name, set_point):
        song = app.player.song
        if not song:
            return

        a_point, b_point = app.player.get_ab_points()

        pos = app.player.get_position() // 1000 if set_point else None
        if name == "A":
            a_point = pos
        elif name == "B":
            b_point = pos

        app.player.set_ab_points(a_point, b_point)
        self.emit("changed")
