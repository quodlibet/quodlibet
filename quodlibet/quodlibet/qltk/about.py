# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk
import mutagen

from quodlibet import const
from quodlibet import formats
from quodlibet.util import fver

class AboutQuodLibet(gtk.AboutDialog):
    def __init__(self, parent, player):
        super(AboutQuodLibet, self).__init__()
        self.set_name("Quod Libet")
        self.set_version(const.VERSION)
        self.set_authors(const.AUTHORS)
        self.set_artists(const.ARTISTS)
        fmts = ", ".join(formats.modules)
        text = []
        text.append(_("Supported formats: %s") % fmts)
        text.append(_("Audio device: %s") % player.name)
        text.append("Mutagen: %s" % fver(mutagen.version))
        text.append("GTK+: %s / PyGTK: %s" %(
            fver(gtk.gtk_version), fver(gtk.pygtk_version)))
        text.append(player.version_info)
        self.set_comments("\n".join(text))
        # Translators: Replace this with your name/email to have it appear
        # in the "About" dialog.
        self.set_translator_credits(_('translator-credits'))
        self.set_website("http://www.sacredchao.net/quodlibet")
        self.set_copyright(
            "Copyright © 2004-2007 Joe Wreschnig, Michael Urman, & others\n"
            "<quodlibet@lists.sacredchao.net>")
        self.child.show_all()

def show(window, player):
    about = AboutQuodLibet(window, player)
    about.run()
    about.destroy()
