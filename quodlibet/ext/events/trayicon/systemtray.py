# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from quodlibet import _
from quodlibet import app
from quodlibet import config
from quodlibet import util
from quodlibet.pattern import Pattern
from quodlibet.qltk import Icons
from quodlibet.util.thumbnails import scale

from .base import BaseIndicator
from .menu import IndicatorMenu
from .util import pconfig


def get_paused_pixbuf(boundary, diff):
    """Returns a pixbuf for a paused icon from the current theme.
    The returned pixbuf can have a size of size->size+diff

    size needs to be > 0
    """

    size = min(boundary)

    if size <= 0:
        raise ValueError("size has to be > 0")

    if diff < 0:
        raise ValueError("diff has to be >= 0")

    names = (Icons.MEDIA_PLAYBACK_PAUSE,)
    theme = Gtk.IconTheme.get_default()

    # Get the suggested icon
    info = theme.choose_icon(names, size, Gtk.IconLookupFlags.USE_BUILTIN)
    if not info:
        return

    try:
        pixbuf = info.load_icon()
    except GLib.GError:
        pass
    else:
        # In case it is too big, rescale
        pb_size = min(pixbuf.get_height(), pixbuf.get_width())
        if abs(pb_size - size) > diff:
            return scale(pixbuf, boundary)
        return pixbuf


def new_with_paused_emblem(icon_pixbuf):
    """Returns a new pixbuf with a pause emblem in the right bottom corner

    (success, new pixbuf)
    """

    padding = 1.0 / 15.0
    size = 5.0 / 8.0

    base = icon_pixbuf.copy()
    w, h = base.get_width(), base.get_height()
    hpad = int(h * padding)
    wpad = int(w * padding)

    # get the sqare area where we can place the icon
    hn = int((w - wpad) * size)
    wn = int((h - hpad) * size)
    if hn <= 0 or wn <= 0:
        return False, base

    # get a pixbuf with roughly the size we want
    overlay = get_paused_pixbuf((hn, wn), min(hn, wn) / 5)
    if not overlay:
        return False, base

    wo, ho = overlay.get_width(), overlay.get_height()
    # we expect below that the icon fits into the icon including padding
    wo = min(w - wpad, wo)
    ho = min(h - hpad, ho)
    overlay.composite(
        base,
        w - wo - wpad,
        h - ho - hpad,
        wo,
        ho,
        w - wo - wpad,
        h - ho - hpad,
        1.0,
        1.0,
        GdkPixbuf.InterpType.BILINEAR,
        255,
    )

    return True, base


class SystemTray(BaseIndicator):
    """A wrapper for Gtk.StatusIcon with some added features,
    workarounds for bugs etc..
    """

    def __init__(self):
        self.__size = -1
        self.__pixbuf = None
        self.__pixbuf_paused = None
        self.__menu = None

        self._icon = Gtk.StatusIcon()
        self.__icon_theme = Gtk.IconTheme.get_default()
        self.__theme_sig = self.__icon_theme.connect("changed", self.__theme_changed)

        self._icon.connect("size-changed", self.__size_changed)
        self._icon.connect("notify::embedded", self.__embedded_changed)
        self.__embedded_changed(self._icon)
        self._icon.connect("popup-menu", self.__popup_menu)
        self._icon.connect("activate", self.__button_left)

        self._icon.connect("scroll-event", self.__scroll)
        self._icon.connect("button-press-event", self.__button_middle)

        self.__w_sig_del = app.window.connect("delete-event", self.__window_delete)

        # If after the main loop is idle and 3 seconds have passed
        # the tray icon isn't embedded, assume it won't be and unhide
        # all windows, so QL isn't 'lost'..

        def add_timeout():
            def check_embedded():
                is_embedded = self._icon.is_embedded()
                main_window_shown = app.window.get_visible()
                if not is_embedded and not main_window_shown:
                    app.present()
                self.__emb_sig = None
                return False

            self.__emb_sig = GLib.timeout_add(3000, check_embedded)
            return False

        self.__emb_sig = GLib.idle_add(add_timeout)

    def remove(self):
        """Hides the tray icon and frees all resources.

        Can only be called once.
        """

        if self.__menu:
            self.__menu.destroy()
            self.__menu = None
        if self.__emb_sig:
            GLib.source_remove(self.__emb_sig)
            self.__emb_sig = None
        self.__icon_theme.disconnect(self.__theme_sig)
        self.__icon_theme = None
        app.window.disconnect(self.__w_sig_del)
        self._icon.set_visible(False)
        self._icon = None
        self.__show_window()

    def set_info_song(self, song):
        """Updates the tooltip based on the passed song"""

        if not self._icon:
            return

        if song:
            try:
                pattern = Pattern(pconfig.get("tooltip"))
            except ValueError:
                tooltip = ""
            else:
                tooltip = pattern % song
        else:
            tooltip = _("Not playing")

        self._icon.set_tooltip_markup(util.escape(tooltip))

    def set_paused(self, paused):
        """Update the icon base on the paused state"""

        self.__update_icon()

    def popup_menu(self):
        """Show the context menu as if the icon was pressed.

        Mainly for testing
        """

        if not self._icon:
            return

        self.__popup_menu(
            self._icon, Gdk.BUTTON_SECONDARY, Gtk.get_current_event_time()
        )

    def __embedded_changed(self, icon, *args):
        if icon.get_property("embedded"):
            size = icon.get_size()
            self.__size_changed(icon, size)

    def __user_can_unhide(self):
        """Return if the user has the possibility to show the Window somehow"""

        if sys.platform == "darwin":
            return False

        # Either if it's embedded, or if we are waiting for the embedded check
        return bool(self._icon.is_embedded() or self.__emb_sig)

    def __update_icon(self):
        if self.__size <= 0:
            return

        if not self.__pixbuf:
            flags = 0
            if sys.platform == "win32":
                flags = Gtk.IconLookupFlags.FORCE_SIZE
            try:
                self.__pixbuf = self.__icon_theme.load_icon(
                    Icons.QUODLIBET, self.__size, flags
                )
            except GLib.GError:
                util.print_exc()
                return

        # We need to fill the whole height that is given to us, or
        # the KDE panel will emit size-changed until we reach 0
        w, h = self.__pixbuf.get_width(), self.__pixbuf.get_height()
        if h < self.__size:
            bg = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, w, self.__size)
            bg.fill(0)
            self.__pixbuf.copy_area(0, 0, w, h, bg, 0, (self.__size - h) / 2)
            self.__pixbuf = bg

        if app.player.paused and not self.__pixbuf_paused:
            self.__pixbuf_paused = new_with_paused_emblem(self.__pixbuf)[1]

        if app.player.paused:
            new_pixbuf = self.__pixbuf_paused
        else:
            new_pixbuf = self.__pixbuf

        self._icon.set_from_pixbuf(new_pixbuf)

    def __theme_changed(self, theme, *args):
        self.__pixbuf = None
        self.__pixbuf_paused = None
        self.__update_icon()

    def __size_changed(self, icon, req_size, *args):
        # https://bugzilla.gnome.org/show_bug.cgi?id=733647
        # Workaround: if size < 16, create a 16px pixbuf anyway and return that
        # we didn't set the right size

        size = max(req_size, 16)
        if size != self.__size:
            self.__pixbuf = None
            self.__pixbuf_paused = None

            self.__size = size
            self.__update_icon()

        return size == req_size and self.__pixbuf is not None

    def __window_delete(self, win, event):
        if self.__user_can_unhide() and pconfig.getboolean("window_hide"):
            self.__hide_window()
            return True
        return False

    def __hide_window(self):
        app.hide()

    def __show_window(self):
        app.present()

    def __button_left(self, icon):
        if self.__destroy_win32_menu():
            return
        if app.window.get_property("visible"):
            self.__hide_window()
        else:
            self.__show_window()

    def __button_middle(self, widget, event, _last_timestamp=[0]):  # noqa
        if (
            event.type == Gdk.EventType.BUTTON_PRESS
            and event.button == Gdk.BUTTON_MIDDLE
        ):
            if self.__destroy_win32_menu():
                return
            # work around gnome shell (3.14) bug, it sends middle clicks twice
            # with the same timestamp, so ignore the second event
            if event.time == _last_timestamp[0]:
                return
            _last_timestamp[0] = event.time
            self.__play_pause()

    def __play_pause(self, *args):
        app.player.playpause()

    def __scroll(self, widget, event):
        state = event.get_state()
        try:
            state ^= pconfig.getboolean("modifier_swap")
        except config.Error:
            pass

        Dir = Gdk.ScrollDirection  # noqa
        if event.direction in [Dir.LEFT, Dir.RIGHT]:
            state = Gdk.ModifierType.SHIFT_MASK

        player = app.player
        if state & Gdk.ModifierType.SHIFT_MASK:
            if event.direction in [Dir.UP, Dir.LEFT]:
                player.previous()
            elif event.direction in [Dir.DOWN, Dir.RIGHT]:
                player.next()
        else:
            if event.direction in [Dir.UP, Dir.LEFT]:
                player.volume += 0.05
            elif event.direction in [Dir.DOWN, Dir.RIGHT]:
                player.volume -= 0.05

    def __destroy_win32_menu(self):
        """Returns True if current action should only hide the menu"""

        if sys.platform in ("win32", "darwin") and self.__menu:
            self.__menu.destroy()
            self.__menu = None
            return True

    def __popup_menu(self, icon, button, time):
        if self.__destroy_win32_menu():
            return
        self.__menu = menu = IndicatorMenu(app)
        menu.set_paused(app.player.paused)
        menu.set_song(app.player.song)
        menu.show_all()

        if sys.platform in ("win32", "darwin"):
            pos_func = pos_arg = None
        else:
            pos_func = Gtk.StatusIcon.position_menu
            pos_arg = self._icon

        menu.popup(None, None, pos_func, pos_arg, button, time)
