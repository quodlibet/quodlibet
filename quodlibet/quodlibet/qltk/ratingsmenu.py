# -*- coding: utf-8 -*-
# Copyright 2011-2013 Nick Boultbee
#           2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import util
from quodlibet import config
from quodlibet import qltk
from quodlibet.config import RATINGS
from quodlibet.qltk import SeparatorMenuItem


class ConfirmRateMultipleDialog(qltk.Message):
    def __init__(self, parent, action_title, count, value):
        assert count > 1

        title = (_("Are you sure you want to change the "
                   "rating of all %d songs?") % count)
        desc = (_("The saved ratings will be removed") if value is None
                else _("The rating of all selected songs will be changed to "
                       "'%s'") % util.format_rating(value))

        super(ConfirmRateMultipleDialog, self).__init__(
            Gtk.MessageType.WARNING, parent, title, desc, Gtk.ButtonsType.NONE)

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_button(action_title, Gtk.ResponseType.YES)


class RatingsMenuItem(Gtk.MenuItem):

    def __init__(self, songs, library, label=_("_Rating")):
        super(RatingsMenuItem, self).__init__(label=label, use_underline=True)
        self.set_songs(songs)

        submenu = Gtk.Menu()
        self.set_submenu(submenu)
        for i in RATINGS.all:
            itm = Gtk.MenuItem(label="%0.2f\t%s" % (i, util.format_rating(i)))
            submenu.append(itm)
            itm.connect('activate', self._on_rating_change, i, library)
        reset = Gtk.MenuItem(label=_("_Remove Rating"), use_underline=True)
        reset.connect('activate', self._on_rating_remove, library)

        submenu.append(SeparatorMenuItem())
        submenu.append(reset)
        submenu.show_all()

    def set_songs(self, songs):
        """Set a new set of songs affected by the rating menu"""

        self._songs = songs

    def _on_rating_change(self, menuitem, value, library):
        self.set_rating(value, self._songs, library)

    def _on_rating_remove(self, menutitem, library):
        self.remove_rating(self._songs, library)

    def set_rating(self, value, songs, librarian):
        count = len(songs)
        if (count > 1 and
                config.getboolean("browsers", "rating_confirm_multiple")):
            parent = qltk.get_menu_item_top_parent(self)
            dialog = ConfirmRateMultipleDialog(
                parent, _("Change _Rating"), count, value)
            if dialog.run() != Gtk.ResponseType.YES:
                return
        for song in songs:
            song["~#rating"] = value
        librarian.changed(songs)

    def remove_rating(self, songs, librarian):
        count = len(songs)
        if (count > 1 and
                config.getboolean("browsers", "rating_confirm_multiple")):
            parent = qltk.get_menu_item_top_parent(self)
            dialog = ConfirmRateMultipleDialog(
                parent, _("_Remove Rating"), count, None)
            if dialog.run() != Gtk.ResponseType.YES:
                return
        reset = []
        for song in songs:
            if "~#rating" in song:
                del song["~#rating"]
                reset.append(song)
        librarian.changed(reset)
