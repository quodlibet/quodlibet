# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk
import qltk

class TextEdit(gtk.Window):
    def __init__(self, parent, default):
        super(TextEdit, self).__init__()
        self.set_title(_("Edit Display"))
        self.set_transient_for(qltk.get_top_parent(parent))
        self.set_border_width(12)
        self.set_default_size(400, 200)
        self.add(gtk.VBox(spacing=12))

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(gtk.TextView())
        self.child.pack_start(sw)
        self.buffer = sw.child.get_buffer()

        box = gtk.HButtonBox()
        box.set_spacing(12)
        box.set_layout(gtk.BUTTONBOX_END)
        rev = gtk.Button(stock=gtk.STOCK_REVERT_TO_SAVED)
        app = gtk.Button(stock=gtk.STOCK_APPLY)
        box.pack_start(rev)
        box.pack_start(app)
        self.child.pack_start(box, expand=False)

        rev.connect_object('clicked', self.buffer.set_text, default)
        self.apply = app
        self.show_all()
