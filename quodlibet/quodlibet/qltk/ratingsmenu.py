# -*- coding: utf-8 -*-
# Copyright 2011, 2012 Nick Boultbee
#           2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
from quodlibet import util, config
from quodlibet import qltk
from gettext import ngettext


class ConfirmRateMultipleDialog(qltk.Message):
    def __init__(self, parent, count, value):
        assert count > 1

        title = (_("Are you sure you want to change the "
                   "rating of all %d songs?") % count)
        description = _("The rating of all selected songs will "
                        "be changed to '%s'") % util.format_rating(value)

        super(ConfirmRateMultipleDialog, self).__init__(
            gtk.MESSAGE_WARNING, parent, title, description, gtk.BUTTONS_NONE)

        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_APPLY, gtk.RESPONSE_YES)


class RatingsMenuItem(gtk.MenuItem):
    __accels = gtk.AccelGroup()

    def set_rating(self, value, songs, librarian):
        count = len(songs)
        if (count > 1 and
                config.getboolean("browsers", "rating_confirm_multiple")):
            dialog = ConfirmRateMultipleDialog(self, count, value)
            if dialog.run() != gtk.RESPONSE_YES:
                return
        for song in songs:
            song["~#rating"] = value
        librarian.changed([song])

    def __init__(self, songs, library, label=_("_Rating")):
        super(RatingsMenuItem, self).__init__(label)
        submenu = gtk.Menu()
        self.set_submenu(submenu)
        for i in range(0, int(1.0 / util.RATING_PRECISION) + 1):
            i *= util.RATING_PRECISION
            itm = gtk.MenuItem("%0.2f\t%s" % (i, util.format_rating(i)))
            submenu.append(itm)
            itm.connect_object('activate', self.set_rating, i, songs, library)
        submenu.show_all()
