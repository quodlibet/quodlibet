# -*- coding: utf-8 -*-
# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gtk
import pango
try:
    import egg.trayicon as trayicon
except ImportError:
    import _trayicon as trayicon

import browsers
import config
import const
import qltk
import stock
import util

from parse import Pattern
from plugins.events import EventPlugin
from qltk.browser import LibraryBrowser
from qltk.controls import StopAfterMenu
from qltk.information import Information
from qltk.properties import SongProperties

from gtk.gdk import SCROLL_LEFT, SCROLL_RIGHT, SCROLL_UP, SCROLL_DOWN

class Preferences(gtk.VBox):
    """A small window to configure the tray icon's tooltip."""

    def __init__(self, activator, player):
        super(Preferences, self).__init__(spacing=12)

        self.set_border_width(6)

        combo = gtk.combo_box_new_text()
        combo.append_text(_("Scroll wheel adjusts volume\n"
                            "Shift and scroll wheel changes song"))
        combo.append_text(_("Scroll wheel changes song\n"
                            "Shift and scroll wheel adjusts volume"))
        try: combo.set_active(int(
            config.getboolean("plugins", "icon_modifier_swap")))
        except config.error: combo.set_active(0)
        combo.connect('changed', self.__changed_combo)
        self.pack_start(qltk.Frame(_("Scroll _Wheel"), child=combo))

        box = gtk.VBox(spacing=12)
        table = gtk.Table(2, 4)
        table.set_row_spacings(6)
        table.set_col_spacings(12)
        tips = qltk.Tooltips(self)

        cbs = []
        for i, tag in enumerate([
            "genre", "artist", "album", "discnumber", "part", "tracknumber",
            "title", "version"]):
            cb = gtk.CheckButton(util.tag(tag))
            cb.tag = tag
            cbs.append(cb)
            table.attach(cb, i%4, i%4+1, i//4, i//4+1)
        box.pack_start(table)

        entry = gtk.Entry()
        box.pack_start(entry, expand=False)

        preview = gtk.Label()
        preview.set_ellipsize(pango.ELLIPSIZE_END)
        ev = gtk.EventBox()
        ev.add(preview)
        box.pack_start(ev, expand=False)

        frame = qltk.Frame(_("Tooltip Display"), child=box)
        frame.get_label_widget().set_mnemonic_widget(entry)
        self.pack_start(frame)

        for cb in cbs:
            cb.connect('toggled', self.__changed_cb, cbs, entry)
        entry.connect(
            'changed', self.__changed_entry, cbs, preview, player, tips)
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
        text = "<%s>" % "~".join([cb.tag for cb in cbs if cb.get_active()])
        entry.set_text(text)

    def __changed_entry(self, entry, cbs, label, player, tips):
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
            for cb in cbs: cb.set_inconsistent(True)

        if player.info is None: text = _("Not playing")
        else: text = Pattern(entry.get_text()) % player.info
        label.set_text(text)
        tips.set_tip(label.get_parent(), text)
        config.set("plugins", "icon_tooltip", entry.get_text())

class TrayIcon(EventPlugin):
    __icon = None
    __mapped = False
    __menu = None
    __pattern = Pattern(
        "<album|<album~discnumber~part~tracknumber~title~version>|"
        "<artist~title~version>>")

    PLUGIN_ID = "Tray Icon"
    PLUGIN_NAME = _("Tray Icon")
    PLUGIN_DESC = _("Control Quod Libet from the system tray.")
    PLUGIN_VERSION = "0.23.1"

    def enabled(self):
        from widgets import main as window, watcher
        from player import playlist as player

        self.__menu = self.__Menu(watcher, window, player)
        self.__menu.show_all()
        self.__icon = icon = trayicon.TrayIcon("quodlibet")
        self.__tips = qltk.Tooltips(self.__icon)

        try: filename = os.path.join(const.IMAGEDIR, "quodlibet.")
        except AttributeError:
            filename = os.path.join(const.BASEDIR, "quodlibet.")
        try: p = gtk.gdk.pixbuf_new_from_file_at_size(filename + "svg", 16, 16)
        except:
            p = gtk.gdk.pixbuf_new_from_file_at_size(filename + "png", 16, 16)
        self.__image = gtk.Image()
        if p:
            self.__image.set_from_pixbuf(p)
            self.__pixbuf = p
        eb = gtk.EventBox(); eb.add(self.__image)
        icon.add(eb)

        window.connect('delete-event', self.__window_delete)

        icon.connect('map-event', self.__map, True, window)
        icon.connect('unmap-event', self.__map, False, window)
        icon.connect('button-press-event', self.__button, window, player)
        icon.connect('scroll-event', self.__scroll, window, player)
        icon.connect('destroy', self.__destroy, window)

        icon.show_all()
        self.plugin_on_paused()
        self.plugin_on_song_started(player.song)

    def disabled(self):
        self.__icon.destroy()
        self.__menu.destroy()

    def __destroy(self, icon, window):
        self.__icon = None
        self.__show_window(window)

    def PluginPreferences(self, parent):
        from player import playlist as player
        p = Preferences(self, player)
        p.connect_object('destroy', self.__prefs_destroy, player)
        return p

    def __prefs_destroy(self, player):
        self.plugin_on_song_started(player.info)

    def __enabled(self):
        return (self.__icon  and self.__mapped and
                self.__icon.get_property('visible'))
    is_enabled = property(__enabled)

    def __window_delete(self, window, event):
        if self.is_enabled:
            self.__hide_window(window)
            return True

    def __set_tooltip(self, tooltip):
        if self.__icon: self.__tips.set_tip(self.__icon, tooltip)
    tooltip = property(None, __set_tooltip)

    def __map(self, icon, event, value, window):
        self.__mapped = value
        if not value:
            self.__show_window(window)

    def __hide_window(self, window):
        window.__position = window.get_position()
        window.hide()
        config.set("plugins", "icon_window_visible", "false")

    def __show_window(self, window):
        try: window.move(*window.__position)
        except AttributeError: pass
        window.present()
        config.set("plugins", "icon_window_visible", "true")

    def __button(self, icon, event, window, player):
        if event.button == 1:
            if window.get_property('visible'): self.__hide_window(window)
            else: self.__show_window(window)
        elif event.button == 2: self.__play_pause(icon, player)
        elif event.button == 3: self.__popup(event, window)

    def __play_pause(self, activator, player):
        if player.song:
            player.paused ^= True
        else:
            player.reset()

    def __scroll(self, widget, event, window, player):
        try: event.state ^= config.getboolean("plugins", "icon_modifier_swap")
        except config.error: pass
        if event.direction in [SCROLL_LEFT, SCROLL_RIGHT]:
            event.state = gtk.gdk.SHIFT_MASK
        if event.state & gtk.gdk.SHIFT_MASK:
            if event.direction in [SCROLL_UP, SCROLL_LEFT]: player.previous()
            elif event.direction in [SCROLL_DOWN, SCROLL_RIGHT]: player.next()
        else:
            if event.direction in [SCROLL_UP, SCROLL_LEFT]:
                player.volume += 0.05
            elif event.direction in [SCROLL_DOWN, SCROLL_RIGHT]:
                player.volume -= 0.05

    def plugin_on_song_started(self, song):
        items = self.__menu.sensitives
        for item in items: item.set_sensitive(bool(song))
        if song:
            try:
                p = Pattern(config.get("plugins", "icon_tooltip"))
            except (ValueError, config.error): p = self.__pattern
            self.tooltip = p % song
        else: self.tooltip = _("Not playing")

    def __Menu(self, watcher, window, player):
        playpause = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
        playpause.connect('activate', self.__play_pause, player)
        safter = StopAfterMenu(player)
        playpause.connect(
            'button-press-event', self.__play_button_press, safter)

        previous = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PREVIOUS)
        previous.connect('activate', lambda *args: player.previous())
        next = gtk.ImageMenuItem(gtk.STOCK_MEDIA_NEXT)
        next.connect('activate', lambda *args: player.next())

        orders = gtk.MenuItem(_("Play _Order"))
        submenu = gtk.Menu()
        repeat = gtk.CheckMenuItem(_("_Repeat"))
        repeat.connect(
            'toggled', lambda s: window.repeat.set_active(s.get_active()))
        submenu.append(repeat)
        submenu.append(gtk.SeparatorMenuItem())
        items = [None]
        def set_order(widget, num):
            if widget.get_active(): window.order.set_active(num)
        try:
            from quodlibet.qltk.playorder import ORDERS
        except ImportError:
            for i, s in enumerate([_("_In Order"), _("_Shuffle"),
                                   _("_Weighted"), _("_One Song")]):
                items.append(gtk.RadioMenuItem(items[-1], s))
                items[-1].connect('toggled', set_order, i)
        else:
            for i, Kind in enumerate(ORDERS):
                name = Kind.accelerated_name
                items.append(gtk.RadioMenuItem(items[-1], name))
                items[-1].connect('toggled', set_order, i)
        items.pop(0)
        map(submenu.append, items)
        orders.set_submenu(submenu)

        browse = qltk.MenuItem(_("_Browse Library"), gtk.STOCK_FIND)
        m2 = gtk.Menu()
        from library import library
        for Kind in browsers.browsers:
            i = gtk.MenuItem(Kind.accelerated_name)
            i.connect_object('activate', LibraryBrowser, Kind, library)
            m2.append(i)
        browse.set_submenu(m2)

        props = gtk.ImageMenuItem(stock.EDIT_TAGS)
        props.connect_object('activate', self.__properties, watcher, player)

        info = gtk.ImageMenuItem(gtk.STOCK_INFO)
        info.connect_object('activate', self.__information, watcher, player)

        rating = gtk.Menu()
        def set_rating(value):
            song = player.song
            if song is None: return
            else:
                song["~#rating"] = value
                watcher.changed([song])
        for i in range(0, int(1.0/util.RATING_PRECISION)+1):
            j = i * util.RATING_PRECISION
            item = gtk.MenuItem("%0.2f\t%s" % (j, util.format_rating(j)))
            item.connect_object('activate', set_rating, j)
            rating.append(item)
        ratings = gtk.MenuItem(_("_Rating"))
        ratings.set_submenu(rating)

        quit = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        quit.connect('activate', gtk.main_quit)

        menu = gtk.Menu()
        for item in [playpause,
                     gtk.SeparatorMenuItem(), previous, next, orders,
                     gtk.SeparatorMenuItem(), browse,
                     gtk.SeparatorMenuItem(), props, info, ratings,
                     gtk.SeparatorMenuItem(), quit]:
            menu.append(item)
        menu.repeat = repeat
        menu.orders = items
        menu.sensitives = [props, next, ratings, info]
        safter.connect_object('selection-done', gtk.Menu.popdown, menu)
        return menu

    def __play_button_press(self, activator, event, safter):
        if event.button == 3:
            safter.popup(None, None, None, event.button, event.time)
            return True

    def __popup(self, event, window):
        order = window.order.get_active()
        self.__menu.orders[order].set_active(True)
        self.__menu.repeat.set_active(window.repeat.get_active())
        self.__menu.popup(None, None, None, event.button, event.time)
        return True

    def plugin_on_paused(self):
        from player import playlist as player
        playpause = self.__menu.get_children()[0]
        stock = [gtk.STOCK_MEDIA_PAUSE, gtk.STOCK_MEDIA_PLAY][player.paused]
        img = gtk.image_new_from_stock(stock, gtk.ICON_SIZE_MENU)
        playpause.set_image(img)
        playpause.child.set_text(gtk.stock_lookup(stock)[1])
        playpause.child.set_use_underline(True)

        if player.paused:
            base = self.__pixbuf.copy()
            overlay = self.__image.render_icon(gtk.STOCK_MEDIA_PAUSE,
                    gtk.ICON_SIZE_MENU)
            w, h = base.get_width(), base.get_height()
            overlay.composite(base, w // 3, h // 3, 2 * w // 3, 2 * h // 3,
                    w // 3, h // 3, 0.75, 0.75, gtk.gdk.INTERP_BILINEAR, 255)
            #overlay.composite(base, 0, 0, w, h, 0, 0, 1, 1,
                    #gtk.gdk.INTERP_BILINEAR, 92)
            self.__image.set_from_pixbuf(base)
        else:
            self.__image.set_from_pixbuf(self.__pixbuf)

    plugin_on_unpaused = plugin_on_paused

    def __properties(self, watcher, player):
        if player.song:
            SongProperties(watcher, [player.song])

    def __information(self, watcher, player):
        if player.song:
            Information(watcher, [player.song])

    def destroy(self):
        if self.__icon: self.__icon.destroy()
        if self.__menu: self.__menu.destroy()
