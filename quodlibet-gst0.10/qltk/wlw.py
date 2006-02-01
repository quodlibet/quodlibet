# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk
from qltk import get_top_parent

class WaitLoadWindow(gtk.Window):
    """A window with a progress bar and some nice updating text,
    as well as pause/stop buttons.

    Example:

    w = WaitLoadWindow(None, 5, "%d/%d", (0, 5))
    for i in range(1, 6): w.step(i, 5)
    w.destroy()
    """

    def __init__(self, parent, count, text, initial=(), limit=5):
        """parent: the parent window, or None
        count: the total amount of items expected, or 0 for unknown/indefinite
        text: text to display in the window; may contain % formats
        initial: initial values for % formats (text % initial)
        limit: count must be greater than limit (or 0) for pause/stop to appear

        The current iteration of the counter can be gotten as
        window.current. count can be gotten as window.count.
        """

        super(WaitLoadWindow, self).__init__()
        if parent:
            parent = get_top_parent(parent)
            sig = parent.connect('configure-event', self.__recenter)
            self.connect_object(
                'destroy', WaitLoadWindow.__disconnect, self, sig)
            self.set_transient_for(parent)
            parent.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        self.set_modal(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_focus_on_map(False)
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
        while gtk.events_pending(): gtk.main_iteration()
        self.show_all()

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

class WritingWindow(WaitLoadWindow):
    """A WaitLoadWindow that defaults to text suitable for saving files."""

    def __init__(self, parent, count):
        super(WritingWindow, self).__init__(
            parent, count,
            (_("Saving the songs you changed.") + "\n\n" +
             _("%d/%d songs saved")), (0, count))

    def step(self):
        return super(WritingWindow, self).step(self.current + 1, self.count)
