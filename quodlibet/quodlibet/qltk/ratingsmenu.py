# -*- coding: utf-8 -*-
# Copyright 2011, 2012 Nick Boultbee
#           2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import util
from quodlibet import config
from quodlibet import qltk


class ConfirmRateMultipleDialog(qltk.Message):
    def __init__(self, parent, count, value):
        assert count > 1

        title = (_("Are you sure you want to change the "
                   "rating of all %d songs?") % count)
        description = _("The rating of all selected songs will "
                        "be changed to '%s'") % util.format_rating(value)

        super(ConfirmRateMultipleDialog, self).__init__(
            Gtk.MessageType.WARNING, parent, title, description,
            Gtk.ButtonsType.NONE)

        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_APPLY, Gtk.ResponseType.YES)


class RatingsMenuItem(Gtk.MenuItem):
    __accels = Gtk.AccelGroup()

    def set_rating(self, value, songs, librarian):
        count = len(songs)
        if (count > 1 and
                config.getboolean("browsers", "rating_confirm_multiple")):
            dialog = ConfirmRateMultipleDialog(self, count, value)
            if dialog.run() != Gtk.ResponseType.YES:
                return
        for song in songs:
            song["~#rating"] = value
        librarian.changed([song])

    def __init__(self, songs, library, label=_("_Rating")):
        super(RatingsMenuItem, self).__init__(label=label, use_underline=True)
        submenu = Gtk.Menu()
        self.set_submenu(submenu)
        for i in range(0, int(1.0 / util.RATING_PRECISION) + 1):
            i *= util.RATING_PRECISION
            itm = Gtk.MenuItem("%0.2f\t%s" % (i, util.format_rating(i)))
            submenu.append(itm)
            itm.connect_object('activate', self.set_rating, i, songs, library)
        submenu.show_all()
