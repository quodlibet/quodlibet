# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Widget wrappers for GTK.
import gtk
import util

class Notebook(gtk.Notebook):
    def append_page(self, page, label = None):
        if label is not None:
            if not isinstance(label, gtk.Widget): label = gtk.Label(label)
            gtk.Notebook.append_page(self, page, label)
        else:
            if hasattr(page, 'title'):
                title = page.title
                if not isinstance(title, gtk.Widget): title = gtk.Label(title)
                if not isinstance(page, gtk.Widget): page = page.widget
                gtk.Notebook.append_page(self, page, title)
            else: raise TypeError("no page.title and no label given")

def Frame(label = None, border = 0, markup = None, big = False, bold = False,
          alignment = True, child = None, underline = True):
    if markup and label:
        raise ArgumentError("Frame must take only one of label or markup")
    if isinstance(label, basestring):
        format = "%s"
        if big: format = "<big>%s</big>" % format
        if bold: format  = "<b>%s</b>" % format
        if label: markup = util.escape(label)
        markup = format % markup
        label = gtk.Label()
        label.set_markup(markup)
        if underline: label.set_use_underline(True)

    frame = gtk.Frame()
    frame.set_border_width(border)
    if alignment:
        align = gtk.Alignment(xalign = 0.0, yalign = 0.0,
                              xscale = 1.0, yscale = 1.0)
        
        align.set_padding(3, 0, 12, 0)
        frame.add(align)
        if child: align.add(child)
    elif child: frame.add(child)
    frame.set_shadow_type(gtk.SHADOW_NONE)
    frame.set_label_widget(label)
    return frame

def Button(text = None, image = None, stock = None, cb = None, user_data = []):
    # Regular GTK stock button.
    if stock: b = gtk.Button(stock = stock)
    else:
        # Label-only button.
        if image is None: b = gtk.Button(text)
        else:
            # Stock image with custom label.
            hbox = gtk.HBox(spacing = 2)
            i = gtk.Image()
            i.set_from_stock(image, gtk.ICON_SIZE_BUTTON)
            hbox.pack_start(i)
            l = gtk.Label(text)
            l.set_use_underline(True)
            hbox.pack_start(l)
            b = gtk.Button()
            b.add(hbox)
    # Set a callback.
    if cb: b.connect('clicked', cb, *user_data)
    return b
