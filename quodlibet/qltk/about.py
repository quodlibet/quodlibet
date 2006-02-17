# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gtk
import gst
import const
import formats

def fver(tup): return ".".join(map(str, tup))

class AboutWindow(gtk.AboutDialog):
    def __init__(self, parent, player, run=True):
        gtk.AboutDialog.__init__(self)
        self.set_name("Quod Libet")
        self.set_version(const.VERSION)
        self.set_authors(const.AUTHORS)
        fmts = ", ".join(formats.modules)
        text = []
        text.append(_("Supported formats: %s") % fmts)
        text.append(_("Audio device: %s") % player.name)
        text.append("GTK+: %s / PyGTK: %s" %(
            fver(gtk.gtk_version), fver(gtk.pygtk_version)))
        text.append("GStreamer: %s / PyGSt: %s" %(
            fver(gst.version()), fver(gst.pygst_version)))
        self.set_comments("\n".join(text))
        # Translators: Replace this with your name/email to have it appear
        # in the "About" dialog.
        self.set_translator_credits(_('translator-credits'))
        self.set_website("http://www.sacredchao.net/quodlibet")
        self.set_copyright(
            "Copyright © 2004-2005 Joe Wreschnig, Michael Urman, & others\n"
            "<quodlibet@lists.sacredchao.net>")
        if run: gtk.AboutDialog.run(self)
        self.destroy()

