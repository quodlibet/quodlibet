# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

import quodlibet
from quodlibet import const


class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent, app):
        super(AboutDialog, self).__init__()
        self.set_transient_for(parent)
        self.set_program_name(app.name)
        self.set_version(quodlibet.get_build_description())
        self.set_authors(const.AUTHORS)
        self.set_artists(const.ARTISTS)
        self.set_logo_icon_name(app.icon_name)
        self.set_comments(app.description)
        self.set_license_type(Gtk.License.GPL_2_0)
        self.set_translator_credits("\n".join(const.TRANSLATORS))
        self.set_website(const.WEBSITE)
        self.set_copyright(const.COPYRIGHT + "\n" +
                           "<%s>" % const.SUPPORT_EMAIL)
