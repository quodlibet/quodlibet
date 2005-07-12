# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Widget wrappers for GTK.
import os
import gobject, gtk
import config
import util

class Message(gtk.MessageDialog):
    """A message dialog that destroys itself after it is run, uses
    markup, and defaults to an 'OK' button."""

    def __init__(self, kind, parent, title, description, buttons=None):
        buttons = buttons or gtk.BUTTONS_OK
        text = "<span size='xx-large'>%s</span>\n\n%s" % (title, description)
        gtk.MessageDialog.__init__(
            self, parent, gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            kind, buttons)
        self.set_markup(text)

    def run(self, destroy=True):
        gtk.MessageDialog.run(self)
        if destroy: self.destroy()

class ConfirmAction(Message):
    """A message dialog that asks a yes/no question."""

    def __init__(self, *args, **kwargs):
        kwargs["buttons"] = gtk.BUTTONS_YES_NO
        Message.__init__(self, gtk.MESSAGE_WARNING, *args, **kwargs)

    def run(self, destroy = True):
        """Returns True if yes was clicked, False otherwise."""
        resp = gtk.MessageDialog.run(self)
        if destroy: self.destroy()
        if resp == gtk.RESPONSE_YES: return True
        else: return False

class ErrorMessage(Message):
    """Like Message, but uses an error-indicating picture."""
    def __init__(self, *args):
        Message.__init__(self, gtk.MESSAGE_ERROR, *args)

class WarningMessage(Message):
    """Like Message, but uses an warning-indicating picture."""
    def __init__(self, *args):
        Message.__init__(self, gtk.MESSAGE_WARNING, *args)

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

class ConfigCheckButton(gtk.CheckButton):
    """A CheckButton that connects to QL's config module, and toggles
    a boolean configuration value when it is toggled.

    It is *not* set to the current config value initially."""

    def __init__(self, label, section, option):
        gtk.CheckButton.__init__(self, label)
        self.connect('toggled', ConfigCheckButton.__toggled, section, option)

    def __toggled(self, section, option):
        config.set(section, option, str(bool(self.get_active())).lower())

class ComboBoxEntrySave(gtk.ComboBoxEntry):
    """A ComboBoxEntry that remembers the past 'count' strings entered,
    and can save itself to (and load itself from) a filename or file-like."""

    models = {}
    
    def __init__(self, f=None, initial=[], count=10, model=None):
        self.count = count
        if model:
            try:
                gtk.ComboBoxEntry.__init__(self, self.models[model], 0)
            except KeyError:
                gtk.ComboBoxEntry.__init__(self, gtk.ListStore(str), 0)
                self.models[model] = self.get_model()
                self.__fill(f, initial)
        else:
            gtk.ComboBoxEntry.__init__(self, gtk.ListStore(str), 0)
            self.__fill(f, initial)
        self.connect_object('destroy', self.set_model, None)

    def __fill(self, f, initial):
        if f is not None and not hasattr(f, 'readlines'):
            if os.path.exists(f):
                for line in file(f).readlines():
                    self.append_text(line.strip())
        elif f is not None:
            for line in f.readlines():
                self.append_text(line.strip())
        for c in initial: self.append_text(c)

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
        """Return a list of all entries in the history."""
        return [m[0] for m in self.get_model()]

    def write(self, f, create=True):
        """Save to f, a filename or file-like. If create is True, any
        needed parent directories will be created."""
        try:
            if not hasattr(f, 'read'):
                if ("/" in f and create and
                    not os.path.isdir(os.path.dirname(f))):
                    os.makedirs(os.path.dirname(f))
                f = file(f, "w")
            f.write("\n".join(self.get_text()) + "\n")
        except (IOError, OSError): pass

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

def Button(text, image):
    # Stock image with custom label.
    hbox = gtk.HBox(spacing=2)
    i = gtk.Image()
    i.set_from_stock(image, gtk.ICON_SIZE_BUTTON)
    hbox.pack_start(i)
    l = gtk.Label(text)
    l.set_use_underline(True)
    hbox.pack_start(l)
    b = gtk.Button()
    b.add(hbox)
    return b

class ValidatingEntry(gtk.Entry):
    """An entry with visual feedback as to whether it is valid or not.
    The given validator function gets a string and returns True (green),
    False (red), or a color string, or None (black).

    parser.is_valid_color mimicks the behavior of the search bar.

    If the "Color search terms" option is off, the entry will not
    change color."""

    def __init__(self, validator=None, *args):
        gtk.Entry.__init__(self, *args)
        if validator: self.connect_object('changed', self.__color, validator)

    def __color(self, validator):
        if not config.getboolean('browsers', 'color'): return
        value = validator(self.get_text())
        if value is True: color = "dark green"
        elif value is False: color = "red"
        elif isinstance(value, str): color = value
        else: color = None

        if color: gobject.idle_add(self.__set_color, color)

    def __set_color(self, color):
        if self.get_property('sensitive'):
            layout = self.get_layout()
            text = layout.get_text()
            markup = '<span foreground="%s">%s</span>' %(
                color, util.escape(text))
            layout.set_markup(markup)

class WaitLoadWindow(gtk.Window):
    """A window with a progress bar and some nice updating text,
    as well as pause/stop buttons.

    Example:

    w = WaitLoadWindow(None, 5, "%d/%d", (0, 5))
    for i in range(1, 6): w.step(i, 5)
    w.destroy()
    """

    def __init__(self, parent, count, text, initial=(), limit=5,
                 show=True):
        """parent: the parent window, or None
        count: the total amount of items expected, or 0 unknown/indefinite
        text: text to display in the window; may contain % formats
        initial: initial values for % formats (text % initial)
        limit: count must be greater than limit (or 0) for pause/stop to appear
        show: show the window right away; you want this to be True

        The current iteration of the counter can be gotten as
        window.current. count can be gotten as window.count.
        """

        gtk.Window.__init__(self)
        if parent:
            sig = parent.connect('configure-event', self.__recenter)
            self.connect_object(
                'destroy', WaitLoadWindow.__disconnect, self, sig)
            self.set_transient_for(parent)
            parent.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        self.set_modal(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.add(gtk.Frame())
        self.child.set_shadow_type(gtk.SHADOW_OUT)
        vbox = gtk.VBox(spacing=12)
        vbox.set_border_width(12)
        self.__label = gtk.Label()
        self.__label.set_size_request(170, -1)
        self.__label.set_use_markup(True)
        self.__label.set_line_wrap(True)
        self.__label.set_justify(gtk.JUSTIFY_CENTER)
        vbox.pack_start(self.__label)
        self.__progress = gtk.ProgressBar()
        self.__progress.set_pulse_step(0.08)
        vbox.pack_start(self.__progress)

        self.current = 0
        self.count = count
        if self.count > limit or self.count == 0:
            # Display a stop/pause box. count = 0 means an indefinite
            # number of steps.
            hbox = gtk.HBox(spacing=6, homogeneous=True)
            b1 = gtk.Button(stock=gtk.STOCK_STOP)
            b2 = gtk.ToggleButton(gtk.STOCK_MEDIA_PAUSE)
            b2.set_use_stock(True)
            b1.connect('clicked', self.__cancel_clicked)
            b2.connect('clicked', self.__pause_clicked)
            hbox.pack_start(b1)
            hbox.pack_start(b2)
            vbox.pack_start(hbox)

        self.child.add(vbox)

        self.__text = text
        self.__paused = False
        self.__quit = False

        self.__label.set_markup(self.__text % initial)
        self.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        if show: self.show_all()
        while gtk.events_pending(): gtk.main_iteration()

    def __pause_clicked(self, button):
        self.__paused = button.get_active()

    def __cancel_clicked(self, button):
        self.__quit = True

    def step(self, *values):
        """Advance the counter by one. Arguments are applied to the
        originally-supplied text as a format string.

        This function doesn't return if the dialog is paused (though
        the GTK main loop will still run), and returns True if stop
        was pressed.
        """

        self.__label.set_markup(self.__text % values)
        if self.count:
            self.current += 1
            self.__progress.set_fraction(
                max(0, min(1, self.current / float(self.count))))
        else:
            self.__progress.pulse()

        while not self.__quit and (self.__paused or gtk.events_pending()):
            gtk.main_iteration()
        return self.__quit

    def __recenter(self, parent, event):
        x, y = parent.get_position()
        dx, dy = parent.get_size()
        dx2, dy2 = self.get_size()
        self.move(x + dx/2 - dx2/2, y + dy/2 - dy2/2)

    def __disconnect(self, sig):
        self.get_transient_for().window.set_cursor(None)
        self.get_transient_for().disconnect(sig)

class RPaned(object):
    """A Paned that supports relative (percentage) width/height setting."""

    _v = None # Not implemented
    def get_relative(self):
        if self.get_property('max-position') > 0:
            return float(self.get_position())/self.get_property('max-position')
        else: return 0.5

    def set_relative(self, v):
        return self.set_position(int(v * self.get_property('max-position')))

class RHPaned(RPaned, gtk.HPaned): _v = 0
class RVPaned(RPaned, gtk.VPaned): _v = 1
