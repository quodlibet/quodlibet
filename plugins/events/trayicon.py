# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import sys

from gi.repository import Gtk, Pango, Gdk, GdkPixbuf, GLib

from quodlibet import browsers, config, qltk, util, app
from quodlibet.parse import Pattern
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk.browser import LibraryBrowser
from quodlibet.qltk.controls import StopAfterMenu
from quodlibet.qltk.information import Information
from quodlibet.qltk.playorder import ORDERS
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.x import RadioMenuItem
from quodlibet.util.thumbnails import scale, calc_scale_size


class Preferences(Gtk.VBox):
    """A small window to configure the tray icon's tooltip."""

    def __init__(self, activator):
        super(Preferences, self).__init__(spacing=12)

        self.set_border_width(6)

        combo = Gtk.ComboBoxText()
        combo.append_text(_("Scroll wheel adjusts volume\n"
                            "Shift and scroll wheel changes song"))
        combo.append_text(_("Scroll wheel changes song\n"
                            "Shift and scroll wheel adjusts volume"))
        combo.set_active(int(
                config.getboolean("plugins", "icon_modifier_swap", False)))
        combo.connect('changed', self.__changed_combo)

        self.pack_start(qltk.Frame(_("Scroll _Wheel"), child=combo),
                        True, True, 0)

        box = Gtk.VBox(spacing=12)
        table = Gtk.Table(2, 4)
        table.set_row_spacings(6)
        table.set_col_spacings(12)

        cbs = []
        for i, tag in enumerate([
                "genre", "artist", "album", "discnumber", "part",
                "tracknumber", "title", "version"]):
            cb = Gtk.CheckButton(util.tag(tag))
            cb.tag = tag
            cbs.append(cb)
            table.attach(cb, i % 3, i % 3 + 1, i // 3, i // 3 + 1)
        box.pack_start(table, True, True, 0)

        entry = Gtk.Entry()
        box.pack_start(entry, False, True, 0)

        preview = Gtk.Label()
        preview.set_ellipsize(Pango.EllipsizeMode.END)
        ev = Gtk.EventBox()
        ev.add(preview)
        box.pack_start(ev, False, True, 0)

        frame = qltk.Frame(_("Tooltip Display"), child=box)
        frame.get_label_widget().set_mnemonic_widget(entry)
        self.pack_start(frame, True, True, 0)

        for cb in cbs:
            cb.connect('toggled', self.__changed_cb, cbs, entry)
        entry.connect(
            'changed', self.__changed_entry, cbs, preview)
        try:
            entry.set_text(config.get("plugins", "icon_tooltip"))
        except:
            entry.set_text(
                "<album|<album~discnumber~part~tracknumber~title~version>|"
                "<artist~title~version>>")

        self.show_all()

    def __changed_combo(self, combo):
        config.set(
            "plugins", "icon_modifier_swap", str(bool(combo.get_active())))

    def __changed_cb(self, cb, cbs, entry):
        text = "<%s>" % "~".join([c.tag for c in cbs if c.get_active()])
        entry.set_text(text)

    def __changed_entry(self, entry, cbs, label):
        text = entry.get_text()
        if text[0:1] == "<" and text[-1:] == ">":
            parts = text[1:-1].split("~")
            for cb in cbs:
                if parts and parts[0] == cb.tag:
                    parts.pop(0)
            if parts:
                for cb in cbs:
                    cb.set_inconsistent(True)
            else:
                parts = text[1:-1].split("~")
                for cb in cbs:
                    cb.set_inconsistent(False)
                    cb.set_active(cb.tag in parts)
        else:
            for cb in cbs:
                cb.set_inconsistent(True)

        if app.player.info is None:
            text = _("Not playing")
        else:
            text = Pattern(entry.get_text()) % app.player.info
        label.set_text(text)
        label.get_parent().set_tooltip_text(text)
        config.set("plugins", "icon_tooltip", entry.get_text())


class TrayIcon(EventPlugin):
    __icon = None
    __pixbuf = None
    __pixbuf_paused = None
    __icon_theme = None
    __menu = None
    __size = -1
    __w_sig_map = None
    __w_sig_del = None
    __theme_sig = None
    __stop_after = None
    __first_map = True
    __pattern = Pattern(
        "<album|<album~discnumber~part~tracknumber~title~version>|"
        "<artist~title~version>>")

    PLUGIN_ID = "Tray Icon"
    PLUGIN_NAME = _("Tray Icon")
    PLUGIN_DESC = _("Control Quod Libet from the system tray.")
    PLUGIN_VERSION = "2.0"

    def enabled(self):
        self.__icon = Gtk.StatusIcon()
        self.__icon_theme = Gtk.IconTheme.get_default()
        self.__theme_sig = self.__icon_theme.connect('changed',
            self.__theme_changed)

        self.__icon.connect('size-changed', self.__size_changed)
        #no size-changed under win32
        if sys.platform == "win32":
            self.__size = 16

        self.__icon.connect('popup-menu', self.__button_right)
        self.__icon.connect('activate', self.__button_left)

        self.__icon.connect('scroll-event', self.__scroll)
        self.__icon.connect('button-press-event', self.__button_middle)

        self.__w_sig_map = app.window.connect('map', self.__window_map)
        self.__w_sig_del = app.window.connect('delete-event',
                                              self.__window_delete)

        self.__stop_after = StopAfterMenu(app.player)

        self.plugin_on_paused()
        self.plugin_on_song_started(app.player.song)

    def disabled(self):
        self.__icon_theme.disconnect(self.__theme_sig)
        self.__icon_theme = None
        self.__stop_after = None
        app.window.disconnect(self.__w_sig_map)
        app.window.disconnect(self.__w_sig_del)
        self.__icon.set_visible(False)
        try:
            self.__icon.destroy()
        except AttributeError:
            pass
        self.__icon = None
        self.__show_window()

    def PluginPreferences(self, parent):
        p = Preferences(self)
        p.connect('destroy', self.__prefs_destroy)
        return p

    def __get_paused_pixbuf(self, size, diff):
        """Returns a pixbuf for a paused icon frokm the current theme.
        The returned pixbuf can have a size of size->size+diff"""

        names = ('media-playback-pause', Gtk.STOCK_MEDIA_PAUSE)
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
            if pixbuf.get_height() - size > diff:
                return scale(pixbuf, (size,) * 2)
            return pixbuf

    def __update_icon(self):
        if self.__size <= 0:
            return

        if not self.__pixbuf:
            try:
                self.__pixbuf = self.__icon_theme.load_icon(
                    "quodlibet", self.__size, 0)
            except GLib.GError:
                util.print_exc()
                return

        #we need to fill the whole height that is given to us, or
        #the KDE panel will emit size-changed until we reach 0
        w, h = self.__pixbuf.get_width(), self.__pixbuf.get_height()
        if h < self.__size:
            bg = GdkPixbuf.Pixbuf(
                GdkPixbuf.Colorspace.RGB, True, 8, w, self.__size)
            bg.fill(0)
            self.__pixbuf.copy_area(0, 0, w, h, bg, 0, (self.__size - h) / 2)
            self.__pixbuf = bg

        if app.player.paused and not self.__pixbuf_paused:
            base = self.__pixbuf.copy()
            w, h = base.get_width(), base.get_height()
            pad = h / 15

            # get the area where we can place the icon
            wn, hn = calc_scale_size((w - pad, 5 * (h - pad) / 8), (1, 1))

            # get a pixbuf with roughly the size we want
            diff = (h - hn - pad) / 3
            overlay = self.__get_paused_pixbuf(hn, diff)

            if overlay:
                wo, ho = overlay.get_width(), overlay.get_height()

                overlay.composite(base, w - wo - pad, h - ho - pad,
                    wo, ho, w - wo - pad, h - ho - pad,
                    1, 1,
                    GdkPixbuf.InterpType.BILINEAR, 255)

            self.__pixbuf_paused = base

        if app.player.paused:
            new_pixbuf = self.__pixbuf_paused
        else:
            new_pixbuf = self.__pixbuf

        self.__icon.set_from_pixbuf(new_pixbuf)

    def __theme_changed(self, theme, *args):
        self.__pixbuf = None
        self.__pixbuf_paused = None
        self.__update_icon()

    def __size_changed(self, icon, size, *args):
        if size != self.__size:
            self.__pixbuf = None
            self.__pixbuf_paused = None

            self.__size = size
            self.__update_icon()
        return True

    def __prefs_destroy(self, *args):
        if self.__icon:
            self.plugin_on_song_started(app.player.song)

    def __window_delete(self, win, event):
        return self.__hide_window()

    def __window_map(self, win):
        visible = config.getboolean("plugins", "icon_window_visible", False)

        config.set("plugins", "icon_window_visible", "true")

        #only restore window state on start
        if not visible and self.__first_map:
            self.__hide_window()

    def __hide_window(self):
        self.__first_map = False
        app.hide()
        config.set("plugins", "icon_window_visible", "false")
        return True

    def __show_window(self):
        app.present()

    def __button_left(self, icon):
        if self.__destroy_win32_menu():
            return
        if app.window.get_property('visible'):
            self.__hide_window()
        else:
            self.__show_window()

    def __button_middle(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 2:
            if self.__destroy_win32_menu():
                return
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
            state ^= config.getboolean("plugins", "icon_modifier_swap")
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

    def plugin_on_song_started(self, song):
        if not self.__icon:
            return

        if song:
            try:
                pattern = Pattern(config.get("plugins", "icon_tooltip"))
            except (ValueError, config.Error):
                pattern = self.__pattern

            tooltip = pattern % song
        else:
            tooltip = _("Not playing")

        self.__icon.set_tooltip_markup(util.escape(tooltip))

    def __destroy_win32_menu(self):
        """Returns True if current action should only hide the menu"""
        if sys.platform == "win32" and self.__menu:
            self.__menu.destroy()
            self.__menu = None
            return True

    def __button_right(self, icon, button, time):
        if self.__destroy_win32_menu():
            return
        self.__menu = menu = Gtk.Menu()

        player = app.player
        window = app.window

        pp_icon = [Gtk.STOCK_MEDIA_PAUSE, Gtk.STOCK_MEDIA_PLAY][player.paused]
        playpause = Gtk.ImageMenuItem.new_from_stock(pp_icon, None)
        playpause.connect('activate', self.__play_pause)

        previous = Gtk.ImageMenuItem.new_from_stock(
            Gtk.STOCK_MEDIA_PREVIOUS, None)
        previous.connect('activate', lambda *args: player.previous())
        next = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_MEDIA_NEXT, None)
        next.connect('activate', lambda *args: player.next())

        orders = Gtk.MenuItem(label=_("Play _Order"), use_underline=True)

        repeat = Gtk.CheckMenuItem(label=_("_Repeat"), use_underline=True)
        repeat.set_active(window.repeat.get_active())
        repeat.connect('toggled',
            lambda s: window.repeat.set_active(s.get_active()))

        def set_safter(widget, stop_after):
            stop_after.active = widget.get_active()

        safter = Gtk.CheckMenuItem(label=_("Stop _after this song"),
                                   use_underline=True)
        safter.set_active(self.__stop_after.active)
        safter.connect('activate', set_safter, self.__stop_after)

        def set_order(widget, num):
            window.order.set_active(num)

        order_items = []
        item = None
        for i, Kind in enumerate(ORDERS):
            item = RadioMenuItem(
                    group=item,
                    label=Kind.accelerated_name,
                    use_underline=True)
            order_items.append(item)
            item.connect('toggled', set_order, i)

        order_items[window.order.get_active()].set_active(True)

        order_sub = Gtk.Menu()
        order_sub.append(repeat)
        order_sub.append(safter)
        order_sub.append(Gtk.SeparatorMenuItem())
        map(order_sub.append, order_items)
        orders.set_submenu(order_sub)

        browse = qltk.MenuItem(_("_Browse Library"), Gtk.STOCK_FIND)
        browse_sub = Gtk.Menu()

        for Kind in browsers.browsers:
            if not Kind.in_menu:
                continue
            i = Gtk.MenuItem(label=Kind.accelerated_name, use_underline=True)
            i.connect_object('activate', LibraryBrowser, Kind, app.library)
            browse_sub.append(i)

        browse.set_submenu(browse_sub)

        props = qltk.MenuItem(_("Edit _Tags"), Gtk.STOCK_PROPERTIES)
        props.connect('activate', self.__properties)

        info = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_INFO, None)
        info.connect('activate', self.__information)

        rating = Gtk.MenuItem(label=_("_Rating"), use_underline=True)
        rating_sub = Gtk.Menu()

        def set_rating(value):
            song = player.song
            if song is None:
                return
            else:
                song["~#rating"] = value
                app.librarian.changed([song])

        for i in range(0, int(1.0 / util.RATING_PRECISION) + 1):
            j = i * util.RATING_PRECISION
            item = Gtk.MenuItem("%0.2f\t%s" % (j, util.format_rating(j)))
            item.connect_object('activate', set_rating, j)
            rating_sub.append(item)

        rating.set_submenu(rating_sub)

        quit = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT, None)
        quit.connect('activate', lambda *x: app.quit())

        menu.append(playpause)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(previous)
        menu.append(next)
        menu.append(orders)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(browse)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(props)
        menu.append(info)
        menu.append(rating)
        menu.append(Gtk.SeparatorMenuItem())
        menu.append(quit)

        menu.show_all()

        if sys.platform == "win32":
            menu.popup(None, None, None, button, time, self.__icon)
        else:
            menu.popup(None, None, Gtk.StatusIcon.position_menu, self.__icon,
                button, time)

    plugin_on_paused = __update_icon
    plugin_on_unpaused = __update_icon

    def __properties(self, *args):
        song = app.player.song
        if song:
            SongProperties(app.librarian, [song])

    def __information(self, *args):
        song = app.player.song
        if song:
            Information(app.librarian, [song])
