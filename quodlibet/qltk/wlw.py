# Copyright 2005 Joe Wreschnig, Michael Urman
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import math
import time

from gi.repository import Gtk, Pango, Gdk

from quodlibet import _
from quodlibet.qltk import get_top_parent, Icons, Button, ToggleButton
from quodlibet.util import format_int_locale, format_time_display


class WaitLoadBase:
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

        super().__init__()

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
            self._cancel_button = Button(_("_Stop"), Icons.PROCESS_STOP)
            self._pause_button = ToggleButton(_("P_ause"),
                                              Icons.MEDIA_PLAYBACK_PAUSE)
            self._cancel_button.connect('clicked', self.__cancel_clicked)
            self._pause_button.connect('clicked', self.__pause_clicked)
        else:
            self._cancel_button = None
            self._pause_button = None

    def setup(self, count=0, text="", initial=None):
        self.current = 0
        self.count = count
        self._text = text
        self.paused = False
        self.quit = False
        self._start_time = time.time()
        initial = initial or {}

        initial.setdefault("total", self.count)
        initial.setdefault("current", self.current)
        initial.setdefault("remaining", _("Unknown"))

        def localeify(k, v):
            foo = '%(' + k + ')d'
            if foo in self._text:
                self._text = self._text.replace(foo, '%(' + k + ')s')
                return k, format_int_locale(int(v))
            return k, v

        localed = dict(localeify(k, v) for k, v in initial.items())
        self._label.set_markup(self._text % localed)
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
        values.setdefault("total", format_int_locale(self.count))
        values.setdefault("current", format_int_locale(self.current))
        if self.count:
            t = (time.time() - self._start_time) / self.current
            remaining = math.ceil((self.count - self.current) * t)
            values.setdefault("remaining", format_time_display(remaining))
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
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.set_decorated(False)
        WaitLoadBase.__init__(self)
        self.setup(*args)

        parent = get_top_parent(parent)
        if parent:
            sig = parent.connect('configure-event', self.__recenter)
            self.connect('destroy', self.__reset_cursor, parent)
            self.connect('destroy', self.__disconnect, sig, parent)
            sig_vis = parent.connect(
                'visibility-notify-event', self.__update_visible)
            self.connect('destroy', self.__disconnect, sig_vis, parent)
            self.set_transient_for(parent)
            window = parent.get_window()
            if window:
                window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        # Note that this should not be modal as popups occuring during
        # progress will not be clickable
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

        self.get_child().show_all()
        while Gtk.events_pending():
            Gtk.main_iteration()

    def __update_visible(self, parent, event):
        if event.state == Gdk.VisibilityState.FULLY_OBSCURED:
            self.hide()
        else:
            self.show()

    def __recenter(self, parent, event):
        x, y = parent.get_position()
        dx, dy = parent.get_size()
        dx2, dy2 = self.get_size()
        self.move(x + dx // 2 - dx2 // 2, y + dy // 2 - dy2 // 2)

    def __disconnect(self, widget, sig, parent):
        parent.disconnect(sig)

    def __reset_cursor(self, widget, parent):
        if parent.get_window():
            parent.get_window().set_cursor(None)


class WritingWindow(WaitLoadWindow):
    """A WaitLoadWindow that defaults to text suitable for saving files."""

    def __init__(self, parent, count):
        super().__init__(
            parent, count,
            (_("Saving the songs you changed.") + "\n\n" +
             _("%(current)d/%(total)d songs saved\n(%(remaining)s remaining)")
            ))

    def step(self):
        return super().step()


class WaitLoadBar(WaitLoadBase, Gtk.HBox):
    def __init__(self):
        super().__init__()

        self._label.set_alignment(0.0, 0.5)
        self._label.set_ellipsize(Pango.EllipsizeMode.END)

        self._cancel_button.remove(self._cancel_button.get_child())
        self._cancel_button.add(Gtk.Image.new_from_icon_name(
            Icons.PROCESS_STOP, Gtk.IconSize.MENU))
        self._pause_button.remove(self._pause_button.get_child())
        self._pause_button.add(Gtk.Image.new_from_icon_name(
            Icons.MEDIA_PLAYBACK_PAUSE, Gtk.IconSize.MENU))

        self.pack_start(self._label, True, True, 0)
        self.pack_start(self._progress, False, True, 6)
        self.pack_start(self._pause_button, False, True, 0)
        self.pack_start(self._cancel_button, False, True, 0)

        for child in self.get_children():
            child.show_all()

    def step(self, **values):
        ret = super().step(**values)
        params = {"current": format_int_locale(self.current),
                  "all": format_int_locale(self.count)}
        self._progress.set_text(_("%(current)s of %(all)s") % params)
        return ret
