# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk

import config
import const
import browsers
import pattern
import player
import util
import qltk

from properties import SongProperties
from qltk import LibraryBrowser

class TrayIcon(object):
    __icon = False
    __mapped = False
    __tips = gtk.Tooltips()
    __tips.enable()
    __menu = None
    __pattern = pattern.Pattern(
        "<album|<album~discnumber~part~tracknumber~title~version>|"
        "<artist~title~version>>")

    def __init__(self, watcher, window):
        try: import egg.trayicon as trayicon
        except ImportError:
            try: import trayicon
            except: return

        self.__menu = self.__Menu(watcher, window)
        self.__menu.show_all()

        self.__mapped = False
        self.__icon = icon = trayicon.TrayIcon("quodlibet")
        self.__tips.enable()
        p = gtk.gdk.pixbuf_new_from_file_at_size("quodlibet.png", 16, 16)
        img = gtk.Image(); img.set_from_pixbuf(p)
        eb = gtk.EventBox(); eb.add(img)
        icon.add(eb)

        window.connect('delete-event', self.__window_delete)

        icon.connect('map-event', self.__map, True)
        icon.connect('unmap-event', self.__map, False)
        icon.connect('button-press-event', self.__button, window)
        icon.connect('scroll-event', self.__scroll, window)

        watcher.connect('song-started', self.__song_started)
        watcher.connect('paused', self.__set_paused, True)
        watcher.connect('unpaused', self.__set_paused, False)

        icon.show_all()

    def __enabled(self):
        return (self.__icon  and self.__mapped and
                self.__icon.get_property('visible'))
    enabled = property(__enabled)

    def __window_delete(self, window, event):
        if self.enabled:
            self.hide_window(window)
            return True

    def __set_tooltip(self, tooltip):
        if self.__icon: self.__tips.set_tip(self.__icon, tooltip)
    tooltip = property(None, __set_tooltip)

    def __map(self, icon, event, value):
        self.__mapped = value

    def hide_window(self, window):
        window.__position = window.get_position()
        window.hide()

    def show_window(self, window):
        window.move(*window.__position)
        window.show()

    def __button(self, icon, event, window):
        if event.button == 1:
            if window.get_property('visible'): self.hide_window(window)
            else: self.show_window(window)
        elif event.button == 2: self.__play_pause(icon)
        elif event.button == 3: self.__popup(event, window)

    def __play_pause(self, activator):
        if player.playlist.song: player.playlist.paused ^= True

    def __scroll(self, widget, event, window):
        if event.direction == gtk.gdk.SCROLL_UP: window.volume += 0.05
        elif event.direction == gtk.gdk.SCROLL_DOWN: window.volume -= 0.05
        elif event.direction == gtk.gdk.SCROLL_LEFT: player.playlist.previous()
        elif event.direction == gtk.gdk.SCROLL_LEFT: player.playlist.next()

    def __song_started(self, watcher, song):
        items = self.__menu.sensitives
        for item in items: item.set_sensitive(bool(song))
        if song:
            try:
                p = pattern.Pattern(config.get("plugins", "icon_tooltip"))
            except ValueError: p = self.__pattern
            self.tooltip = p % song
        else: self.tooltip = _("Not playing")

    def __Menu(self, watcher, window):
        playpause = qltk.MenuItem(const.SM_PLAY, gtk.STOCK_MEDIA_PLAY)
        playpause.connect('activate', self.__play_pause)
        previous = qltk.MenuItem(const.SM_PREVIOUS, gtk.STOCK_MEDIA_PREVIOUS)
        previous.connect('activate', lambda *args: player.playlist.previous())
        next = qltk.MenuItem(const.SM_NEXT, gtk.STOCK_MEDIA_NEXT)
        next.connect('activate', lambda *args: player.playlist.next())

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

        browse = qltk.MenuItem(_("_Browse Library"), gtk.STOCK_FIND)
        m2 = gtk.Menu()
        for id, label, Kind in browsers.get_browsers():
            i = gtk.MenuItem(label)
            i.connect_object('activate', LibraryBrowser, Kind, watcher)
            m2.append(i)
        browse.set_submenu(m2)

        props = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
        props.connect_object('activate', self.__properties, watcher)

        rating = gtk.Menu()
        def set_rating(value):
            song = player.playlist.song
            if song is None: return
            else:
                song["~#rating"] = value
                widgets.watcher.changed([song])
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
                     gtk.SeparatorMenuItem(), props, ratings,
                     gtk.SeparatorMenuItem(), quit]:
            menu.append(item)
        menu.repeat = repeat
        menu.orders = items
        menu.sensitives = [props, next, ratings]
        return menu

    def __popup(self, event, window):
        order = window.order.get_active()
        self.__menu.orders[order].set_active(True)
        self.__menu.repeat.set_active(window.repeat.get_active())
        self.__menu.popup(None, None, None, event.button, event.time)
        return True

    def __set_paused(self, watcher, paused):
        self.__menu.get_children()[0].destroy()
        stock = [gtk.STOCK_MEDIA_PAUSE, gtk.STOCK_MEDIA_PLAY][paused]
        text = [const.SM_PAUSE, const.SM_PLAY][paused]
        playpause = qltk.MenuItem(text, stock)
        playpause.connect('activate', self.__play_pause)
        playpause.show()
        self.__menu.prepend(playpause)

    def __properties(self, watcher):
        if player.playlist.song:
            SongProperties([player.playlist.song], watcher)

    def destroy(self):
        if self.__icon: self.__icon.destroy()
        if self.__menu: self.__menu.destroy()
