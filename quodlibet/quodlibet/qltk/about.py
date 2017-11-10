# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import platform

from gi.repository import Gtk
import mutagen

import quodlibet
from quodlibet import _
from quodlibet.qltk import gtk_version, pygobject_version, get_backend_name
from quodlibet import const
from quodlibet import formats
from quodlibet.util import fver


class AboutDialog(Gtk.AboutDialog):

    def __init__(self, parent, app):
        super(AboutDialog, self).__init__()
        self.set_transient_for(parent)
        self.set_program_name(app.name)
        self.set_version(quodlibet.get_build_description())
        self.set_authors(const.AUTHORS)
        self.set_artists(const.ARTISTS)
        self.set_logo_icon_name(app.icon_name)

        def chunks(l, n):
            return [l[i:i + n] for i in range(0, len(l), n)]

        is_real_player = app.player.name != "Null"

        format_names = sorted([t.format for t in formats.types])
        fmts = ",\n".join(", ".join(c) for c in chunks(format_names, 4))
        text = []
        text.append(_("Supported formats: %s") % fmts)
        text.append("")
        if is_real_player:
            text.append(_("Audio device: %s") % app.player.name)
        text.append("Python: %s" % platform.python_version())
        text.append("Mutagen: %s" % fver(mutagen.version))
        text.append("GTK+: %s (%s)" % (fver(gtk_version), get_backend_name()))
        text.append("PyGObject: %s" % fver(pygobject_version))
        if is_real_player:
            text.append(app.player.version_info)
        self.set_comments("\n".join(text))
        self.set_license_type(Gtk.License.GPL_2_0)
        self.set_translator_credits("\n".join(const.TRANSLATORS))
        self.set_website(const.WEBSITE)
        self.set_copyright(const.COPYRIGHT + "\n" +
                           "<%s>" % const.SUPPORT_EMAIL)
