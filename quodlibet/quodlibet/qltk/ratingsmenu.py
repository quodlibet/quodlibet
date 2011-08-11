# -*- coding: utf-8 -*-
# Copyright 2011 Nick Boultbee
#           2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
from quodlibet import util, config
from quodlibet import qltk
from gettext import ngettext

class RatingsMenuItem(gtk.MenuItem):
    __accels = gtk.AccelGroup()

    def set_rating(self, value, songs, librarian):
        count = len(songs)
        if (count > 1 and
                config.getboolean("browsers", "rating_confirm_multiple")):
            # There are many plural forms in some supported languages
            # Translators: ratings changes for multiple files
            msg = ngettext("You are about to change the rating of %d song.\n"
                            "Do you wish to continue?",
                    "You are about to change the rating of %d songs.\n"
                            "Do you wish to continue?", count) % count
            if not qltk.ConfirmAction(self, _("Confirm rating"), msg).run():
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
