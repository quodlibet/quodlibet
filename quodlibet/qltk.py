# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Widget wrappers for GTK.
import os
import gtk
import util

# A dialog window with "smart" formatting for the text, uses markup, and
# defaults to an "OK" button, destroying itself after running.
class Message(gtk.MessageDialog):
    def __init__(self, kind, parent, title, description, buttons = None):
        buttons = buttons or gtk.BUTTONS_OK
        text = "<span size='xx-large'>%s</span>\n\n%s" % (title, description)
        gtk.MessageDialog.__init__(
            self, parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            kind, buttons)
        self.set_markup(text)

    def run(self, destroy = True):
        gtk.MessageDialog.run(self)
        if destroy: self.destroy()

class ErrorMessage(Message):
    def __init__(self, *args):
        Message.__init__(self, gtk.MESSAGE_ERROR, *args)

class WarningMessage(Message):
    def __init__(self, *args):
        Message.__init__(self, gtk.MESSAGE_WARNING, *args)

class Notebook(gtk.Notebook):
    def append_page(self, page, label = None):
        if label is not None:
            if not isinstance(label, gtk.Widget): label = gtk.Label(label)
            gtk.Notebook.append_page(self, page, label)
        else:
            if hasattr(page, 'title'):
                title = page.title
                if not isinstance(title, gtk.Widget): title = gtk.Label(title)
                gtk.Notebook.append_page(self, page, title)
            else: raise TypeError("no page.title and no label given")

# A ComboBoxEntry that "remembers" its contents and saves to/loads from
# a file on disk.
class ComboBoxEntrySave(gtk.ComboBoxEntry):
    def __init__(self, f = None, initial = [], count = 10):
        model = gtk.ListStore(str)
        gtk.ComboBoxEntry.__init__(self, model, 0)
        self.count = count
        if f is not None and not hasattr(f, 'readlines'):
            if os.path.exists(f):
                for line in file(f).readlines():
                    self.append_text(line.strip())
        elif f is not None:
            for line in f.readlines():
                self.append_text(line.strip())
        for c in initial: self.append_text(c)
        self.connect('destroy', ComboBoxEntrySave._clean)

    def prepend_text(self, text):
        try: self.remove_text(self.get_text().index(text))
        except ValueError: pass
        gtk.ComboBoxEntry.prepend_text(self, text)
        while len(self.get_model()) > self.count:
            self.remove_text(self.count)

    def insert_text(self, position, text):
        try: self.remove_text(self.get_text().index(text))
        except ValueError: pass
        if position >= self.count: return
        else:
            gtk.ComboBoxEntry.insert_text(self, position, text)
            while len(self.get_model()) > self.count:
                self.remove_text(self.count)

    def append_text(self, text):
        if text not in self.get_text():
            if len(self.get_model()) < self.count:
                gtk.ComboBoxEntry.append_text(self, text)

    def get_text(self):
        return [m[0] for m in self.get_model()]

    def write(self, f, create = True):
        if not hasattr(f, 'read'):
            if "/" in f and create and not os.path.isdir(os.path.dirname(f)):
                os.makedirs(os.path.dirname(f))
            f = file(f, "w")
        f.write("\n".join(self.get_text()) + "\n")

    def _clean(self):
        self.get_model().clear()
        self.set_model(None)

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
