# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import math
import time

from gi.repository import Gtk, Pango

from quodlibet.qltk import get_top_parent
from quodlibet import util

class WaitLoadBase(object):
    """Abstract class providing a label, a progressbar, pause/stop buttons,
    and the stepping logic."""

    def __init__(self, count=0, text="", initial={}, limit=3):
        """count: the total amount of items expected, 0 for unknown/indefinite
        text: text to display in the label; may contain % formats
        initial: initial values for % formats (text % initial)
        limit: count must be greater than limit (or 0) for pause/stop to appear

        The current iteration of the counter can be gotten as
        self.current. count can be gotten as self.count.
        """

        super(WaitLoadBase, self).__init__()

        self._label = Gtk.Label()
        self._label.set_use_markup(True)

        self._progress = Gtk.ProgressBar()
        self._progress.set_pulse_step(0.08)
        self.pulse = self._progress.pulse
        self.set_fraction = self._progress.set_fraction
        self.set_text = self._label.set_markup

        self.setup(count, text, initial)

        if self.count > limit or self.count == 0:
            # Add stop/pause buttons. count = 0 means an indefinite
            # number of steps.
            self._cancel_button = Gtk.Button(stock=Gtk.STOCK_STOP)
            self._pause_button = Gtk.ToggleButton(Gtk.STOCK_MEDIA_PAUSE)
            self._pause_button.set_use_stock(True)
            self._cancel_button.connect('clicked', self.__cancel_clicked)
            self._pause_button.connect('clicked', self.__pause_clicked)
        else:
            self._cancel_button = None
            self._pause_button = None

    def setup(self, count=0, text="", initial={}):
        self.current = 0
        self.count = count
        self._text = text
        self.paused = False
        self.quit = False
        self._start_time = time.time()

        initial.setdefault("total", self.count)
        initial.setdefault("current", self.current)
        initial.setdefault("remaining", _("Unknown"))
        self._label.set_markup(self._text % initial)
        self._progress.set_fraction(0.0)

    def __pause_clicked(self, button):
        self.paused = button.get_active()

    def __cancel_clicked(self, button):
        self.quit = True

    def step(self, **values):
        """Advance the counter by one. Arguments are applied to the
        originally-supplied text as a format string.

        This function doesn't return if the dialog is paused (though
        the GTK main loop will still run), and returns True if stop
        was pressed.
        """

        if self.count:
            self.current += 1
            self._progress.set_fraction(
                max(0, min(1, self.current / float(self.count))))
        else:
            self._progress.pulse()
        values.setdefault("total", self.count)
        values.setdefault("current", self.current)
        if self.count:
            t = (time.time() - self._start_time) / self.current
            remaining = math.ceil((self.count - self.current) * t)
            values.setdefault("remaining", util.format_time(remaining))
        self._label.set_markup(self._text % values)

        while not self.quit and (self.paused or Gtk.events_pending()):
            Gtk.main_iteration()
        return self.quit

class WaitLoadWindow(WaitLoadBase, Gtk.Window):
    """A window with a progress bar and some nice updating text,
    as well as pause/stop buttons.

    Example:

    w = WaitLoadWindow(None, 5, "%(current)d/%(total)d")
    for i in range(1, 6): w.step()
    w.destroy()
    """

    def __init__(self, parent, *args):
        """parent: the parent window, or None"""

        super(WaitLoadWindow, self).__init__()
        self.setup(*args)

        parent = get_top_parent(parent)
        if parent:
            sig = parent.connect('configure-event', self.__recenter)
            self.connect_object(
                'destroy', WaitLoadWindow.__disconnect, self, sig, parent)
            self.set_transient_for(parent)
            parent.window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        self.set_modal(True)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_focus_on_map(False)
        self.add(Gtk.Frame())
        self.get_child().set_shadow_type(Gtk.ShadowType.OUT)
        vbox = Gtk.VBox(spacing=12)
        vbox.set_border_width(12)
        self._label.set_size_request(170, -1)
        self._label.set_line_wrap(True)
        self._label.set_justify(Gtk.Justification.CENTER)
        vbox.pack_start(self._label, True, True, 0)
        vbox.pack_start(self._progress, True, True, 0)

        if self._cancel_button and self._pause_button:
            # Display a stop/pause box. count = 0 means an indefinite
            # number of steps.
            hbox = Gtk.HBox(spacing=6, homogeneous=True)
            hbox.pack_start(self._cancel_button, True, True, 0)
            hbox.pack_start(self._pause_button, True, True, 0)
            vbox.pack_start(hbox, True, True, 0)

        self.get_child().add(vbox)

        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        while Gtk.events_pending(): Gtk.main_iteration()
        self.show_all()

    def __recenter(self, parent, event):
        x, y = parent.get_position()
        dx, dy = parent.get_size()
        dx2, dy2 = self.get_size()
        self.move(x + dx // 2 - dx2 // 2, y + dy // 2 - dy2 // 2)

    def __disconnect(self, sig, parent):
        if parent.window:
            parent.window.set_cursor(None)
        parent.disconnect(sig)

class WritingWindow(WaitLoadWindow):
    """A WaitLoadWindow that defaults to text suitable for saving files."""

    def __init__(self, parent, count):
        super(WritingWindow, self).__init__(
            parent, count,
            (_("Saving the songs you changed.") + "\n\n" +
             _("%(current)d/%(total)d songs saved\n(%(remaining)s remaining)")))

    def step(self):
        return super(WritingWindow, self).step()

class WaitLoadBar(WaitLoadBase, Gtk.HBox):
    def __init__(self):
        super(WaitLoadBar, self).__init__()

        self._label.set_alignment(0.0, 0.5)
        self._label.set_ellipsize(Pango.EllipsizeMode.END)

        self._cancel_button.remove(self._cancel_button.get_child())
        self._cancel_button.add(Gtk.Image.new_from_stock(
            Gtk.STOCK_STOP, Gtk.IconSize.MENU))
        self._pause_button.remove(self._pause_button.get_child())
        self._pause_button.add(Gtk.Image.new_from_stock(
            Gtk.STOCK_MEDIA_PAUSE, Gtk.IconSize.MENU))

        self.pack_start(self._label, True, True, 0)
        self.pack_start(self._progress, False, True, 6)
        self.pack_start(self._pause_button, False, True, 0)
        self.pack_start(self._cancel_button, False, True, 0)

        self.show_all()

    def step(self, **values):
        ret = super(WaitLoadBar, self).step(**values)
        self._progress.set_text(_("%d of %d") % (self.current, self.count))
        return ret
