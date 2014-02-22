# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk, GLib, GdkPixbuf
import mutagen

from quodlibet.qltk import gtk_version, pygobject_version
from quodlibet import const
from quodlibet import formats
from quodlibet.util import fver


def _set_about_image(dialog, icon_name):
    # win32 workaround: https://bugzilla.gnome.org/show_bug.cgi?id=721062

    if os.name == "nt":
        size = 96
        theme = Gtk.IconTheme.get_default()
        icon_info = theme.lookup_icon(icon_name, size, 0)
        if icon_info is None:
            return

        filename = icon_info.get_filename()
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, size, size)
        except GLib.GError:
            return
        else:
            dialog.set_logo(pb)
    else:
        dialog.set_logo_icon_name(icon_name)


class AboutDialog(Gtk.AboutDialog):
    def __init__(self, parent, player, name, icon):
        super(AboutDialog, self).__init__()
        self.set_transient_for(parent)
        self.set_program_name(name)
        self.set_version(const.VERSION)
        self.set_authors(const.AUTHORS)
        self.set_artists(const.ARTISTS)
        _set_about_image(self, icon)

        def chunks(l, n):
            return [l[i:i + n] for i in range(0, len(l), n)]

        fmts = ",\n".join(", ".join(c) for c in chunks(formats.names, 4))
        text = []
        text.append(_("Supported formats: %s") % fmts)
        text.append("")
        if player:
            text.append(_("Audio device: %s") % player.name)
        text.append("Mutagen: %s" % fver(mutagen.version))
        text.append("GTK+: %s" % fver(gtk_version))
        text.append("PyGObject: %s" % fver(pygobject_version))
        if player:
            text.append(player.version_info)
        self.set_comments("\n".join(text))
        self.set_translator_credits("\n".join(const.TRANSLATORS))
        self.set_website(const.WEBSITE)
        self.set_copyright(const.COPYRIGHT + "\n" +
                           "<%s>" % const.SUPPORT_EMAIL)


class AboutQuodLibet(AboutDialog):
    def __init__(self, parent, player):
        super(AboutQuodLibet, self).__init__(
            parent, player, "Quod Libet", "quodlibet")


class AboutExFalso(AboutDialog):
    def __init__(self, parent, player=None):
        super(AboutExFalso, self).__init__(
            parent, player, "Ex Falso", "exfalso")
