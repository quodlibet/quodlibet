# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gtk
import pango

import const
import stock
import config
import qltk
import util
import browsers

from qltk.properties import SongProperties
from qltk.browser import LibraryBrowser
from qltk.controls import StopAfterMenu
from qltk.information import Information
from parse import Pattern

class Preferences(qltk.Window):
    """A small window to configure the tray icon's tooltip."""

    def __init__(self, activator, watcher):
        super(Preferences, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Tray Icon Preferences") + " - Quod Libet")
        vbox = gtk.VBox(spacing=12)

        combo = gtk.combo_box_new_text()
        combo.append_text(_("Scroll wheel adjusts volume\n"
                            "Shift and scroll wheel changes song"))
        combo.append_text(_("Scroll wheel changes song\n"
                            "Shift and scroll wheel adjusts volume"))
        try: combo.set_active(int(
            config.getboolean("plugins", "icon_modifier_swap")))
        except: combo.set_active(0)
        combo.connect('changed', self.__changed_combo)
        vbox.pack_start(
            qltk.Frame(child=combo, label=_("Scroll Wheel"), bold=True))

        box = gtk.VBox(spacing=12)
        table = gtk.Table(2, 4)
        table.set_row_spacings(6)
        table.set_col_spacings(12)
        current = config.get("plugins", "icon_tooltip")[1:-1].split("~")
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

        vbox.pack_start(
            qltk.Frame(child=box, label=_("Tooltip Display"), bold=True))

        for cb in cbs: cb.connect('toggled', self.__changed_cb, cbs, entry)
        entry.connect(
            'changed', self.__changed_entry, cbs, preview, watcher, tips)
        entry.set_text(config.get("plugins", "icon_tooltip"))

        self.add(vbox)
        self.show_all()

    def __changed_combo(self, combo):
        config.set(
            "plugins", "icon_modifier_swap", str(bool(combo.get_active())))

    def __changed_cb(self, cb, cbs, entry):
        text = "<%s>" % "~".join([cb.tag for cb in cbs if cb.get_active()])
        entry.set_text(text)

    def __changed_entry(self, entry, cbs, label, watcher, tips):
        text = entry.get_text()
        if text[0:1] == "<" and text[-1:] == ">":
            parts = text[1:-1].split("~")
            for cb in cbs:
                if parts and parts[0] == cb.tag: parts.pop(0)
            if parts:
                for cb in cbs: cb.set_inconsistent(True)
            else:
                parts = text[1:-1].split("~")
                for cb in cbs:
                    cb.set_inconsistent(False)
                    cb.set_active(cb.tag in parts)
        else:
            for cb in cbs: cb.set_inconsistent(True)

        if watcher.song is None: text = _("Not playing")
        else: text = Pattern(entry.get_text()) % watcher.song
        label.set_text(text)
        tips.set_tip(label.get_parent(), text)
        config.set("plugins", "icon_tooltip", entry.get_text())

class TrayIcon(object):
    __icon = False
    __mapped = False
    __tips = gtk.Tooltips()
    __tips.enable()
    __menu = None
    __pattern = Pattern(
        "<album|<album~discnumber~part~tracknumber~title~version>|"
        "<artist~title~version>>")

    def __init__(self, watcher, window, player):
        try: import egg.trayicon as trayicon
        except ImportError:
            try: import _trayicon as trayicon
            except: return

        self.__menu = self.__Menu(watcher, window, player)
        self.__menu.show_all()

        self.__mapped = False
        self.__icon = icon = trayicon.TrayIcon("quodlibet")
        self.__tips.enable()
        filename = os.path.join(const.BASEDIR, "quodlibet.")
        try: p = gtk.gdk.pixbuf_new_from_file_at_size(filename + "svg", 16, 16)
        except:
            p = gtk.gdk.pixbuf_new_from_file_at_size(filename + "png", 16, 16)
        img = gtk.Image()
        if p: img.set_from_pixbuf(p)
        eb = gtk.EventBox(); eb.add(img)
        icon.add(eb)

        window.connect('delete-event', self.__window_delete)

        icon.connect('map-event', self.__map, True)
        icon.connect('unmap-event', self.__map, False)
        icon.connect('button-press-event', self.__button, window, player)
        icon.connect('scroll-event', self.__scroll, window, player)

        watcher.connect('song-started', self.__song_started)
        watcher.connect('paused', self.__set_paused, player)
        watcher.connect('unpaused', self.__set_paused, player)

        icon.show_all()

    def __preferences(self, watcher):
        p = Preferences(self, watcher)
        p.connect_object('destroy', self.__prefs_destroy, watcher)

    def __prefs_destroy(self, watcher):
        self.__song_started(watcher, watcher.song)

    def __enabled(self):
        return (self.__icon  and self.__mapped and
                self.__icon.get_property('visible'))
    enabled = property(__enabled)

    def __window_delete(self, window, event):
        if self.enabled:
            self.__hide_window(window)
            return True

    def __set_tooltip(self, tooltip):
        if self.__icon: self.__tips.set_tip(self.__icon, tooltip)
    tooltip = property(None, __set_tooltip)

    def __map(self, icon, event, value):
        self.__mapped = value

    def __hide_window(self, window):
        window.__position = window.get_position()
        window.hide()

    def __show_window(self, window):
        try: window.move(*window.__position)
        except AttributeError: pass
        window.present()

    def __button(self, icon, event, window, player):
        if event.button == 1:
            if window.get_property('visible'): self.__hide_window(window)
            else: self.__show_window(window)
        elif event.button == 2: self.__play_pause(icon, player)
        elif event.button == 3: self.__popup(event, window)

    def __play_pause(self, activator, player):
        if player.song: player.paused ^= True

    def __scroll(self, widget, event, window, player):
        from gtk.gdk import SCROLL_LEFT, SCROLL_RIGHT, SCROLL_UP, SCROLL_DOWN
        try: event.state ^= config.getboolean("plugins", "icon_modifier_swap")
        except: pass
        if event.direction in [SCROLL_LEFT, SCROLL_RIGHT]:
            event.state = gtk.gdk.SHIFT_MASK
        if event.state & gtk.gdk.SHIFT_MASK:
            if event.direction in [SCROLL_UP, SCROLL_LEFT]: player.previous()
            elif event.direction in [SCROLL_DOWN, SCROLL_RIGHT]: player.next()
        else:
            if event.direction in [SCROLL_UP, SCROLL_LEFT]:
                window.volume += 0.05
            elif event.direction in [SCROLL_DOWN, SCROLL_RIGHT]:
                window.volume -= 0.05

    def __song_started(self, watcher, song):
        items = self.__menu.sensitives
        for item in items: item.set_sensitive(bool(song))
        if song:
            try:
                p = Pattern(config.get("plugins", "icon_tooltip"))
            except ValueError: p = self.__pattern
            self.tooltip = p % song
        else: self.tooltip = _("Not playing")

    def __Menu(self, watcher, window, player):
        playpause = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
        playpause.connect('activate', self.__play_pause, player)
        safter = StopAfterMenu(watcher, player)
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
        for i, s in enumerate(
            [_("_In Order"), _("_Shuffle"), _("_Weighted"), _("_One Song")]):
            items.append(gtk.RadioMenuItem(items[-1], s))
            items[-1].connect('toggled', set_order, i)
        items.remove(None)
        map(submenu.append, items)
        orders.set_submenu(submenu)

        preferences = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        preferences.connect_object('activate', self.__preferences, watcher)

        browse = qltk.MenuItem(_("_Browse Library"), gtk.STOCK_FIND)
        m2 = gtk.Menu()
        for id, label, Kind in browsers.get_browsers():
            i = gtk.MenuItem(label)
            i.connect_object('activate', LibraryBrowser, Kind, watcher)
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
                     gtk.SeparatorMenuItem(), preferences, browse,
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

    def __set_paused(self, watcher, player):
        playpause = self.__menu.get_children()[0]
        stock = [gtk.STOCK_MEDIA_PAUSE, gtk.STOCK_MEDIA_PLAY][player.paused]
        img = gtk.image_new_from_stock(stock, gtk.ICON_SIZE_MENU)
        playpause.set_image(img)
        playpause.child.set_text(gtk.stock_lookup(stock)[1])
        playpause.child.set_use_underline(True)

    def __properties(self, watcher, player):
        if player.song: SongProperties(watcher, [player.song])

    def __information(self, watcher, player):
        if player.song: Information(watcher, [player.song])

    def destroy(self):
        if self.__icon: self.__icon.destroy()
        if self.__menu: self.__menu.destroy()
