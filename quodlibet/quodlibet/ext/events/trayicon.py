# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2013 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from quodlibet import browsers, config, qltk, util, app
from quodlibet.config import RATINGS
from quodlibet.pattern import Pattern
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.information import Information
from quodlibet.qltk.playorder import ORDERS
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.window import Window
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.x import RadioMenuItem, SeparatorMenuItem, MenuItem
from quodlibet.qltk import Icons
from quodlibet.util.thumbnails import scale
from quodlibet.util import connect_obj
from quodlibet.plugins import PluginConfig


# migrate option
if config.has_option('plugins', 'trayicon_window_hide'):
    value = config.getboolean('plugins', 'trayicon_window_hide')
    config.remove_option('plugins', 'trayicon_window_hide')
    config.set('plugins', 'icon_window_hide', value)


DEFAULT_PATTERN = ("<album|<album~discnumber~part~tracknumber~title~version>|"
                   "<artist~title~version>>")


pconfig = PluginConfig("icon")
pconfig.defaults.set("window_hide", True)
pconfig.defaults.set("tooltip", DEFAULT_PATTERN)
pconfig.defaults.set("modifier_swap", False)
pconfig.defaults.set("window_visible", True)


class Preferences(Gtk.VBox):
    """A small window to configure the tray icon's tooltip."""

    def __init__(self):
        super(Preferences, self).__init__(spacing=12)

        self.set_border_width(6)

        ccb = pconfig.ConfigCheckButton(_("Hide main window on close"),
                                        'window_hide', populate=True)
        self.pack_start(ccb, False, True, 0)

        combo = Gtk.ComboBoxText()
        combo.append_text(_("Scroll wheel adjusts volume\n"
                            "Shift and scroll wheel changes song"))
        combo.append_text(_("Scroll wheel changes song\n"
                            "Shift and scroll wheel adjusts volume"))
        combo.set_active(int(pconfig.getboolean("modifier_swap")))
        combo.connect('changed', self.__changed_combo)

        self.pack_start(qltk.Frame(_("Scroll _Wheel"), child=combo),
                        True, True, 0)

        box = Gtk.VBox(spacing=12)

        entry_box = Gtk.HBox(spacing=6)

        entry = UndoEntry()
        entry_box.pack_start(entry, True, True, 0)

        def on_reverted(*args):
            pconfig.reset("tooltip")
            entry.set_text(pconfig.gettext("tooltip"))

        revert = Gtk.Button()
        revert.add(Gtk.Image.new_from_icon_name(
            Icons.DOCUMENT_REVERT, Gtk.IconSize.BUTTON))
        revert.connect("clicked", on_reverted)
        entry_box.pack_start(revert, False, True, 0)

        box.pack_start(entry_box, False, True, 0)

        preview = Gtk.Label()
        preview.set_line_wrap(True)
        frame = Gtk.Frame()
        frame.add(preview)
        box.pack_start(frame, False, True, 0)

        frame = qltk.Frame(_("Tooltip Display"), child=box)
        frame.get_label_widget().set_mnemonic_widget(entry)
        self.pack_start(frame, True, True, 0)

        entry.connect('changed', self.__changed_entry, preview, frame)
        entry.set_text(pconfig.gettext("tooltip"))

        for child in self.get_children():
            child.show_all()

    def __changed_combo(self, combo):
        pconfig.set("modifier_swap", bool(combo.get_active()))

    def __changed_entry(self, entry, label, frame):
        text = entry.get_text().decode("utf-8")

        if app.player.info is None:
            text = _("Not playing")
        else:
            text = Pattern(text) % app.player.info

        label.set_text(text)
        frame.set_tooltip_text(text)
        pconfig.set("tooltip", entry.get_text())


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
    overlay.composite(base, w - wo - wpad, h - ho - hpad,
                      wo, ho, w - wo - wpad, h - ho - hpad,
                      1.0, 1.0, GdkPixbuf.InterpType.BILINEAR, 255)

    return True, base


class SysTray(object):
    """A wrapper for Gtk.StatusIcon with some added features,
    workarounds for bugs etc..
    """

    __pattern = Pattern(
        "<album|<album~discnumber~part~tracknumber~title~version>|"
        "<artist~title~version>>")

    def __init__(self):
        self.__size = -1
        self.__pixbuf = None
        self.__pixbuf_paused = None
        self.__menu = None

        self._icon = Gtk.StatusIcon()
        self.__icon_theme = Gtk.IconTheme.get_default()
        self.__theme_sig = self.__icon_theme.connect('changed',
            self.__theme_changed)

        self._icon.connect('size-changed', self.__size_changed)
        self._icon.connect("notify::embedded", self.__embedded_changed)
        self.__embedded_changed(self._icon)
        self._icon.connect('popup-menu', self._popup_menu)
        self._icon.connect('activate', self.__button_left)

        self._icon.connect('scroll-event', self.__scroll)
        self._icon.connect('button-press-event', self.__button_middle)

        self.__w_sig_show = app.window.connect('show', self.__window_show)
        self.__w_sig_del = app.window.connect('delete-event',
                                              self.__window_delete)

        # If after the main loop is idle and 3 seconds have passed
        # the tray icon isn't embedded, assume it wont be and unhide
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

        if sys.platform != "darwin":
            if not pconfig.getboolean("window_visible"):
                Window.prevent_inital_show(True)

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
        app.window.disconnect(self.__w_sig_show)
        app.window.disconnect(self.__w_sig_del)
        self._icon.set_visible(False)
        self._icon = None
        self.__show_window()

    def set_song(self, song):
        """Updates the tooltip based on the passed song"""

        if not self._icon:
            return

        if song:
            try:
                pattern = Pattern(pconfig.get("tooltip"))
            except ValueError:
                pattern = self.__pattern

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

        self._popup_menu(
            self._icon, Gdk.BUTTON_SECONDARY, Gtk.get_current_event_time())

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
                    Icons.QUODLIBET, self.__size, flags)
            except GLib.GError:
                util.print_exc()
                return

        # We need to fill the whole height that is given to us, or
        # the KDE panel will emit size-changed until we reach 0
        w, h = self.__pixbuf.get_width(), self.__pixbuf.get_height()
        if h < self.__size:
            bg = GdkPixbuf.Pixbuf.new(
                GdkPixbuf.Colorspace.RGB, True, 8, w, self.__size)
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

    def __window_show(self, win, *args):
        pconfig.set("window_visible", True)

    def __hide_window(self):
        app.hide()
        pconfig.set("window_visible", False)

    def __show_window(self):
        app.present()

    def __button_left(self, icon):
        if self.__destroy_win32_menu():
            return
        if app.window.get_property('visible'):
            self.__hide_window()
        else:
            self.__show_window()

    def __button_middle(self, widget, event, _last_timestamp=[0]):
        if event.type == Gdk.EventType.BUTTON_PRESS and \
                event.button == Gdk.BUTTON_MIDDLE:
            if self.__destroy_win32_menu():
                return
            # work around gnome shell (3.14) bug, it sends middle clicks twice
            # with the same timestamp, so ignore the second event
            if event.time == _last_timestamp[0]:
                return
            _last_timestamp[0] = event.time
            self.__play_pause()

    def __play_pause(self, *args):
        player = app.player
        if player.song:
            player.paused ^= True
        else:
            player.reset()

    def __scroll(self, widget, event):
        state = event.get_state()
        try:
            state ^= pconfig.getboolean("modifier_swap")
        except config.Error:
            pass

        DIR = Gdk.ScrollDirection
        if event.direction in [DIR.LEFT, DIR.RIGHT]:
            state = Gdk.ModifierType.SHIFT_MASK

        player = app.player
        if state & Gdk.ModifierType.SHIFT_MASK:
            if event.direction in [DIR.UP, DIR.LEFT]:
                player.previous()
            elif event.direction in [DIR.DOWN, DIR.RIGHT]:
                player.next()
        else:
            if event.direction in [DIR.UP, DIR.LEFT]:
                player.volume += 0.05
            elif event.direction in [DIR.DOWN, DIR.RIGHT]:
                player.volume -= 0.05

    def __destroy_win32_menu(self):
        """Returns True if current action should only hide the menu"""

        if sys.platform in ("win32", "darwin") and self.__menu:
            self.__menu.destroy()
            self.__menu = None
            return True

    def _popup_menu(self, icon, button, time):
        if self.__destroy_win32_menu():
            return
        self.__menu = menu = Gtk.Menu()

        player = app.player
        window = app.window

        if player.paused:
            playpause = MenuItem(_("_Play"), Icons.MEDIA_PLAYBACK_START)
        else:
            playpause = MenuItem(_("P_ause"), Icons.MEDIA_PLAYBACK_PAUSE)
        playpause.connect('activate', self.__play_pause)

        previous = MenuItem(_("Pre_vious"), Icons.MEDIA_SKIP_BACKWARD)
        previous.connect('activate', lambda *args: player.previous())

        next = MenuItem(_("_Next"), Icons.MEDIA_SKIP_FORWARD)
        next.connect('activate', lambda *args: player.next())

        orders = Gtk.MenuItem(label=_("Play _Order"), use_underline=True)

        repeat = Gtk.CheckMenuItem(label=_("_Repeat"), use_underline=True)
        repeat.set_active(window.repeat.get_active())
        repeat.connect('toggled',
            lambda s: window.repeat.set_active(s.get_active()))

        def set_safter(widget, safter_action):
            safter_action.set_active(widget.get_active())

        safter_action = app.window.stop_after
        safter = Gtk.CheckMenuItem(label=_("Stop _after this song"),
                                   use_underline=True)
        safter.set_active(safter_action.get_active())
        safter.connect('toggled', set_safter, safter_action)

        def set_order(widget, order):
            name = order.name
            try:
                window.order.set_active_by_name(name)
            except ValueError:
                pass

        order_items = []
        item = None
        active_order = window.order.get_active()
        for Kind in ORDERS:
            item = RadioMenuItem(
                    group=item,
                    label=Kind.accelerated_name,
                    use_underline=True)
            order_items.append(item)
            if Kind is active_order:
                item.set_active(True)
            item.connect('toggled', set_order, Kind)

        order_sub = Gtk.Menu()
        order_sub.append(repeat)
        order_sub.append(safter)
        order_sub.append(SeparatorMenuItem())
        for item in order_items:
            order_sub.append(item)
        orders.set_submenu(order_sub)

        browse = qltk.MenuItem(_("_Browse Library"), Icons.EDIT_FIND)
        browse_sub = Gtk.Menu()

        for Kind in browsers.browsers:
            if Kind.is_empty:
                continue
            i = Gtk.MenuItem(label=Kind.accelerated_name, use_underline=True)
            connect_obj(i,
                'activate', LibraryBrowser.open, Kind, app.library, app.player)
            browse_sub.append(i)

        browse.set_submenu(browse_sub)

        props = qltk.MenuItem(_("Edit _Tags"), Icons.DOCUMENT_PROPERTIES)
        props.connect('activate', self.__properties)

        info = MenuItem(_("_Information"), Icons.DIALOG_INFORMATION)
        info.connect('activate', self.__information)

        def set_rating(value):
            song = player.song
            if song is None:
                return
            else:
                song["~#rating"] = value
                app.librarian.changed([song])

        rating = Gtk.MenuItem(label=_("_Rating"), use_underline=True)
        rating_sub = Gtk.Menu()
        for r in RATINGS.all:
            item = Gtk.MenuItem(label="%0.2f\t%s" % (r, util.format_rating(r)))
            connect_obj(item, 'activate', set_rating, r)
            rating_sub.append(item)
        rating.set_submenu(rating_sub)

        quit = MenuItem(_("_Quit"), Icons.APPLICATION_EXIT)
        quit.connect('activate', lambda *x: app.quit())

        menu.append(playpause)
        menu.append(SeparatorMenuItem())
        menu.append(previous)
        menu.append(next)
        menu.append(orders)
        menu.append(SeparatorMenuItem())
        menu.append(browse)
        menu.append(SeparatorMenuItem())
        menu.append(props)
        menu.append(info)
        menu.append(rating)
        menu.append(SeparatorMenuItem())
        menu.append(quit)

        menu.show_all()

        if sys.platform in ("win32", "darwin"):
            pos_func = pos_arg = None
        else:
            pos_func = Gtk.StatusIcon.position_menu
            pos_arg = self._icon

        menu.popup(None, None, pos_func, pos_arg, button, time)

    def __properties(self, *args):
        song = app.player.song
        if song:
            window = SongProperties(app.librarian, [song])
            window.show()

    def __information(self, *args):
        song = app.player.song
        if song:
            window = Information(app.librarian, [song])
            window.show()


class TrayIcon(EventPlugin):

    PLUGIN_ID = "Tray Icon"
    PLUGIN_NAME = _("Tray Icon")
    PLUGIN_DESC = _("Controls Quod Libet from the system tray.")

    def enabled(self):
        self._tray = SysTray()

    def disabled(self):
        self._tray.remove()
        del self._tray

    def PluginPreferences(self, parent):
        return Preferences()

    def plugin_on_song_started(self, song):
        self._tray.set_song(song)

    def plugin_on_paused(self):
        self._tray.set_paused(True)

    def plugin_on_unpaused(self):
        self._tray.set_paused(False)
