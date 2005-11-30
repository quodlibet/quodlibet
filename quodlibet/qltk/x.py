# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Things that are more or less direct wrappers around GTK widgets to
# ease constructors.

import gobject, gtk
import util

class Window(gtk.Window):
    __gsignals__ = {"close-accel": (
        gobject.SIGNAL_RUN_LAST|gobject.SIGNAL_ACTION, gobject.TYPE_NONE, ())}
    def __init__(self, *args, **kwargs):
        super(Window, self).__init__(*args, **kwargs)
        ag = gtk.AccelGroup()
        self.add_accel_group(ag)
        self.add_accelerator(
            'close-accel', ag, ord('w'), gtk.gdk.CONTROL_MASK, 0)

    def do_close_accel(self):
        self.destroy()
gobject.type_register(Window)

class Notebook(gtk.Notebook):
    """A regular gtk.Notebook, except when appending a page, if no
    label is given, the page's 'title' attribute (either a string or
    a widget) is used."""
    
    def append_page(self, page, label=None):
        if label is not None:
            if not isinstance(label, gtk.Widget): label = gtk.Label(label)
            gtk.Notebook.append_page(self, page, label)
        else:
            if hasattr(page, 'title'):
                title = page.title
                if not isinstance(title, gtk.Widget): title = gtk.Label(title)
                gtk.Notebook.append_page(self, page, title)
            else: raise TypeError("no page.title and no label given")

def Frame(label=None, border=0, bold=False, child=None):
    if isinstance(label, basestring):
        format = "%s"
        if bold: format  = "<b>%s</b>" % format
        markup = util.escape(label)
        markup = format % markup
        label = gtk.Label()
        label.set_markup(markup)
        label.set_use_underline(True)

    frame = gtk.Frame()
    frame.set_border_width(border)
    align = gtk.Alignment(xalign=0.0, yalign=0.0, xscale=1.0, yscale=1.0)
    align.set_padding(3, 0, 12, 0)
    frame.add(align)
    if child: align.add(child)
    frame.set_shadow_type(gtk.SHADOW_NONE)
    frame.set_label_widget(label)
    return frame

def MenuItem(text, image):
    i = gtk.ImageMenuItem(text)
    i.get_image().set_from_stock(image, gtk.ICON_SIZE_MENU)
    return i

def Button(text, image, size=gtk.ICON_SIZE_BUTTON):
    # Stock image with custom label.
    align = gtk.Alignment(xscale=0.0, yscale=1.0, xalign=0.5, yalign=0.5)
    hbox = gtk.HBox(spacing=2)
    i = gtk.Image()
    i.set_from_stock(image, size)
    hbox.pack_start(i)
    l = gtk.Label(text)
    l.set_use_underline(True)
    hbox.pack_start(l)
    align.add(hbox)
    b = gtk.Button()
    b.add(align)
    return b

class RPaned(object):
    """A Paned that supports relative (percentage) width/height setting."""

    def get_relative(self):
        if self.get_property('max-position') > 0:
            return float(self.get_position())/self.get_property('max-position')
        else: return 0.5

    def set_relative(self, v):
        return self.set_position(int(v * self.get_property('max-position')))

class RHPaned(RPaned, gtk.HPaned): pass
class RVPaned(RPaned, gtk.VPaned): pass

class Tooltips(gtk.Tooltips):
    """A Tooltip whose lifetime is tied to another widget's."""
    def __init__(self, parent=None):
        super(Tooltips, self).__init__()
        if parent is not None:
            parent.connect_object('destroy', gtk.Tooltips.destroy, self)
        self.enable()

