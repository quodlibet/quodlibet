# Copyright 2011-2020 Nick Boultbee
#           2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from gi.repository import Gtk

from quodlibet import _
from quodlibet import config
from quodlibet import qltk
from quodlibet.config import RATINGS
from quodlibet.qltk import Icons
from quodlibet.qltk import SeparatorMenuItem
from quodlibet.util import format_rating


class ConfirmRateMultipleDialog(qltk.Message):
    def __init__(self, parent, count: int, value: float | None):
        assert count > 1

        title = _("Are you sure you want to change the rating of all %d songs?") % count
        if value is None:
            desc = _("The saved ratings will be removed")
            action_title = _("_Remove Rating")
        else:
            desc = _(
                "The rating of all selected songs will be changed to %s"
            ) % format_rating(value)
            action_title = _("Change _Rating")

        super().__init__(
            Gtk.MessageType.WARNING, parent, title, desc, Gtk.ButtonsType.NONE
        )

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(action_title, Gtk.ResponseType.YES)


class RatingsMenuItem(Gtk.Button):
    def __init__(self, songs, library, label=_("_Rating")):  # noqa
        super().__init__(use_underline=True)
        self.add_css_class("flat")
        self._songs = songs
        # GTK4: Use Box for icon + label in button
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        icon = Gtk.Image.new_from_icon_name(Icons.FAVORITE)
        box.append(icon)
        box.append(Gtk.Label(label=label, use_underline=True))
        self.set_child(box)

        # GTK4: Buttons don't have submenus; use popover with Box
        submenu = Gtk.PopoverMenu()
        submenu.set_parent(self)
        self._submenu = submenu
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        submenu.set_child(menu_box)

        self._rating_menu_items = []
        for i in RATINGS.all:
            text = f"{i:0.2f}\t{format_rating(i)}"
            itm = Gtk.CheckButton(label=text)
            itm.rating = i
            menu_box.append(itm)
            handler = itm.connect("toggled", self._on_rating_change, i, library)
            self._rating_menu_items.append((itm, handler))

        menu_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        reset = Gtk.Button(label=_("_Remove Rating"), use_underline=True)
        reset.add_css_class("flat")
        reset.connect("clicked", self._on_rating_remove, library)
        menu_box.append(reset)

        self._select_ratings()

        # Connect button to show popover
        self.connect("clicked", lambda w: self._submenu.popup())

    def set_songs(self, songs):
        """Set a new set of songs affected by the rating menu"""
        self._songs = songs
        self._select_ratings()

    def _select_ratings(self):
        ratings = [song("~#rating") for song in self._songs if song and song.has_rating]
        song_count = len(self._songs)
        for menu_item, handler in self._rating_menu_items:
            rating_val = menu_item.rating
            rated_count = ratings.count(rating_val)
            menu_item.handler_block(handler)
            if rated_count == 0:
                menu_item.set_active(False)
            elif rated_count == song_count:
                menu_item.set_active(True)
            else:
                menu_item.set_inconsistent(True)
            menu_item.handler_unblock(handler)

    def _on_rating_change(self, menuitem, value, library):
        self.set_rating(value, self._songs, library)

    def _on_rating_remove(self, menutitem, library):
        self.remove_rating(self._songs, library)

    def set_rating(self, value, songs, librarian):
        count = len(songs)
        if count > 1 and config.getboolean("browsers", "rating_confirm_multiple"):
            parent = qltk.get_menu_item_top_parent(self)
            dialog = ConfirmRateMultipleDialog(parent, count, value)
            if dialog.run() != Gtk.ResponseType.YES:
                return
        for song in songs:
            song["~#rating"] = value
        librarian.changed(songs)

    def remove_rating(self, songs, librarian):
        count = len(songs)
        if count > 1 and config.getboolean("browsers", "rating_confirm_multiple"):
            parent = qltk.get_menu_item_top_parent(self)
            dialog = ConfirmRateMultipleDialog(parent, count, None)
            if dialog.run() != Gtk.ResponseType.YES:
                return
        reset = []
        for song in songs:
            if "~#rating" in song:
                del song["~#rating"]
                reset.append(song)
        librarian.changed(reset)
