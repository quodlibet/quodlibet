# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Things that are more or less direct wrappers around GTK widgets to
# ease constructors.

import gobject
import gtk

from quodlibet import util
from quodlibet.qltk import is_accel
from quodlibet.qltk.window import Window, UniqueWindow


class ScrolledWindow(gtk.ScrolledWindow):
    """Draws a border around all edges that don't touch the parent window"""

    __gsignals__ = {'size-allocate': 'override'}

    def do_size_allocate(self, alloc):
        if self.get_shadow_type() != gtk.SHADOW_NONE:
            ywidth = self.style.ythickness
            xwidth = self.style.xthickness

            # Don't remove the border if the border is drawn inside
            # and the scrollbar on that edge is visible
            bottom = left = right = top = False
            if not self.style_get_property("scrollbars-within-bevel"):
                placement = self.get_placement()
                h, v = self.get_hscrollbar(), self.get_vscrollbar()
                get_visible = lambda w: w.flags() & gtk.VISIBLE
                hscroll = h and get_visible(h) and sum(h.size_request())
                vscroll = v and get_visible(v) and sum(v.size_request())

                if placement == gtk.CORNER_TOP_LEFT:
                    bottom = hscroll
                    right = vscroll
                elif placement == gtk.CORNER_BOTTOM_LEFT:
                    right = vscroll
                    top = hscroll
                elif placement == gtk.CORNER_TOP_RIGHT:
                    bottom = hscroll
                    left = vscroll
                elif placement == gtk.CORNER_BOTTOM_RIGHT:
                    left = vscroll
                    top = hscroll

            parent = self.get_parent_window()
            if parent:
                width, height = parent.get_size()
                if alloc.y + alloc.height == height and not bottom:
                    alloc.height += ywidth

                if alloc.x + alloc.width == width and not right:
                    alloc.width += xwidth
            else:
                gobject.idle_add(self.queue_resize)

            if alloc.y == 0 and not top:
                alloc.y -= ywidth
                alloc.height += ywidth

            if alloc.x == 0 and not left:
                alloc.x -= xwidth
                alloc.width += xwidth

        super(ScrolledWindow, self).do_size_allocate(self, alloc)


class Notebook(gtk.Notebook):
    """A regular gtk.Notebook, except when appending a page, if no
    label is given, the page's 'title' attribute (either a string or
    a widget) is used."""

    __gsignals__ = {'size-allocate': 'override'}

    def do_size_allocate(self, alloc):
        ywidth = self.style.ythickness
        xwidth = self.style.xthickness

        parent = self.get_parent_window()
        if parent:
            width, height = parent.get_size()
            if alloc.y + alloc.height == height:
                alloc.height += ywidth

            if alloc.x + alloc.width == width:
                alloc.width += xwidth
        else:
            gobject.idle_add(self.queue_resize)

        if alloc.x == 0:
            alloc.x -= xwidth
            alloc.width += xwidth

        super(Notebook, self).do_size_allocate(self, alloc)

    def append_page(self, page, label=None):
        if label is None:
            try: label = page.title
            except AttributeError:
                raise TypeError("no page.title and no label given")

        if not isinstance(label, gtk.Widget):
            label = gtk.Label(label)
        super(Notebook, self).append_page(page, label)

def Frame(label, child=None):
    """A gtk.Frame with no shadow, 12px left padding, and 3px top padding."""
    frame = gtk.Frame()
    label_w = gtk.Label()
    label_w.set_markup("<b>%s</b>" % util.escape(label))
    align = gtk.Alignment(xalign=0.0, yalign=0.0, xscale=1.0, yscale=1.0)
    align.set_padding(6, 0, 12, 0)
    frame.add(align)
    frame.set_shadow_type(gtk.SHADOW_NONE)
    frame.set_label_widget(label_w)
    if child:
        align.add(child)
        label_w.set_mnemonic_widget(child)
        label_w.set_use_underline(True)
    return frame

def Alignment(child=None, top=0, bottom=0, left=0, right=0, border=0):
    align = gtk.Alignment(xscale=1.0, yscale=1.0)
    align.set_padding(top + border, bottom + border,
                      left + border, right + border)
    if child:
        align.add(child)
    return align

def MenuItem(label, stock_id):
    """An ImageMenuItem with a custom label and stock image."""
    item = gtk.ImageMenuItem(label)
    item.get_image().set_from_stock(stock_id, gtk.ICON_SIZE_MENU)
    return item

def Button(label, stock_id, size=gtk.ICON_SIZE_BUTTON):
    """A Button with a custom label and stock image. It should pack
    exactly like a stock button."""
    align = gtk.Alignment(xscale=0.0, yscale=1.0, xalign=0.5, yalign=0.5)
    hbox = gtk.HBox(spacing=2)
    hbox.pack_start(gtk.image_new_from_stock(stock_id, size))
    label = gtk.Label(label)
    label.set_use_underline(True)
    hbox.pack_start(label)
    align.add(hbox)
    button = gtk.Button()
    button.add(align)
    return button

class RPaned(object):
    """A Paned that supports relative (percentage) width/height setting."""

    def get_relative(self):
        """Return the relative position of the separator, [0..1]."""
        if self.get_property('max-position') > 0:
            return float(self.get_position())/self.get_property('max-position')
        else: return 0.5

    def set_relative(self, v):
        """Set the relative position of the separator, [0..1]."""
        return self.set_position(int(v * self.get_property('max-position')))

class RHPaned(RPaned, gtk.HPaned): pass
class RVPaned(RPaned, gtk.VPaned): pass

def ClearButton(entry=None):
    clear = gtk.Button()
    clear.add(gtk.image_new_from_stock(gtk.STOCK_CLEAR, gtk.ICON_SIZE_MENU))
    clear.set_tooltip_text(_("Clear search"))
    if entry is not None:
        clear.connect_object('clicked', entry.set_text, '')
    return clear

def EntryCompletion(words):
    """Simple string completion."""
    model = gtk.ListStore(str)
    for word in sorted(words):
        model.append(row=[word])
    comp = gtk.EntryCompletion()
    comp.set_model(model)
    comp.set_text_column(0)
    return comp
