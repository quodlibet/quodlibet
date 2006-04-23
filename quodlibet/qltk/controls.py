# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject, gtk

import stock
import config
import util

import qltk
import qltk.bookmarks
from qltk.sliderbutton import HSlider
from qltk.sliderbutton import VSlider
from qltk.ccb import ConfigCheckMenuItem

SIZE = gtk.ICON_SIZE_LARGE_TOOLBAR

class SeekBar(HSlider):
    __lock = False
    __sig = None
    __seekable = True

    def __init__(self, watcher, player):
        hbox = gtk.HBox(spacing=3)
        l = gtk.Label("0:00")
        hbox.pack_start(l)
        hbox.pack_start(
            gtk.Arrow(gtk.ARROW_RIGHT, gtk.SHADOW_NONE), expand=False)
        super(type(self), self).__init__(hbox)

        self.scale.connect('button-press-event', self.__seek_lock)
        self.scale.connect('button-release-event', self.__seek_unlock, player)
        self.scale.connect('key-press-event', self.__seek_lock)
        self.scale.connect('key-release-event', self.__seek_unlock, player)
        self.connect('scroll-event', self.__scroll, player)
        self.scale.connect('value-changed', self.__update_time, l)

        m = gtk.Menu()
        c = ConfigCheckMenuItem(
            _("Display remaining time"), "player", "time_remaining")
        c.set_active(config.getboolean("player", "time_remaining"))
        c.connect_object('toggled', self.scale.emit, 'value-changed')
        self.__remaining = c
        m.append(c)
        m.append(gtk.SeparatorMenuItem())
        i = qltk.MenuItem(_("_Edit Bookmarks..."), gtk.STOCK_EDIT)
        i.connect_object(
            'activate', qltk.bookmarks.EditBookmarks, self, watcher, player)
        m.append(i)
        m.show_all()
        self.child.connect_object(
            'button-press-event', self.__check_menu, m, player)
        self.connect_object('popup-menu', self.__popup_menu, m, player)

        gobject.timeout_add(1000, self.__check_time, player)
        watcher.connect('song-started', self.__song_changed, l, m)
        watcher.connect_object('seek', self.__seeked, player)

    def __check_menu(self, menu, event, player):
        if event.button == 3:
            return self.__popup_menu(menu, player)

    def __popup_menu(self, menu, player):
        for child in menu.get_children()[2:-1]:
            menu.remove(child)
            child.destroy()

        try: marks = player.song.bookmarks
        except AttributeError: pass # song is None
        else:
            items = qltk.bookmarks.MenuItems(marks, player, self.__seekable)
            items.reverse()
            for i in items: menu.insert(i, 2)
        menu.popup(None, None, None, 0, gtk.get_current_event_time())
        return True

    def __seeked(self, player, song, ms):
        # If it's not paused, we'll grab it in our next update.
        if player.paused: self.scale.set_value(ms//1000)

    def __scroll(self, widget, event, player):
        self.__lock = True
        if self.__sig is not None: gobject.source_remove(self.__sig)
        self.__sig = gobject.timeout_add(100, self.__scroll_timeout, player)

    def __scroll_timeout(self, player):
        self.__lock = False
        if self.__seekable: player.seek(self.scale.get_value() * 1000)
        self.__sig = None

    def __seek_lock(self, scale, event): self.__lock = True
    def __seek_unlock(self, scale, event, player):
        self.__lock = False
        if self.__seekable: player.seek(self.scale.get_value() * 1000)

    def __check_time(self, player):
        # When the song is paused GStreamer returns < 1 for position
        # queries, so if it's paused just ignore it.
        if not (player.paused or self.__lock):
            position = player.get_position() // 1000
            if (not self.__seekable and
                position > self.scale.get_adjustment().upper):
                self.scale.set_range(0, position)
            self.scale.set_value(position)
        return True

    def __update_time(self, scale, timer):
        value = scale.get_value()
        max = scale.get_adjustment().upper
        value -= self.__remaining.get_active() * max
        timer.set_text(util.format_time(value))

    def __song_changed(self, watcher, song, label, menu):
        if song and song.get("~#length", 0) > 0:
            length = song["~#length"]
            self.scale.set_range(0, length)
            self.scale.set_value(0)
            self.__seekable = True
        else:
            self.scale.set_range(0, 1)
            self.scale.set_value(0)
            self.__seekable = False
        for child in menu.get_children()[2:-1]:
            menu.remove(child)
            child.destroy()
        menu.get_children()[-1].set_sensitive(self.__seekable)
        self.scale.emit('value-changed')

class Volume(VSlider):
    def __init__(self, device):
        i = gtk.image_new_from_stock(stock.VOLUME_MAX, SIZE)
        super(type(self), self).__init__(i)
        self.scale.set_update_policy(gtk.UPDATE_CONTINUOUS)
        self.scale.set_inverted(True)
        self.get_value = self.scale.get_value
        self.scale.connect('value-changed', self.__volume_changed, device, i)
        self.set_value(config.getfloat("memory", "volume"))
        self.__volume_changed(self.scale, device, i)
        self.show_all()

    def set_value(self, v):
        self.scale.set_value(max(0.0, min(1.0, v)))

    def __iadd__(self, v):
        self.set_value(min(1.0, self.get_value() + v))
        return self
    def __isub__(self, v):
        self.set_value(max(0.0, self.get_value() - v))
        return self

    def __volume_changed(self, slider, device, image):
        val = slider.get_value()
        if val == 0: img = stock.VOLUME_OFF
        elif val < 0.33: img = stock.VOLUME_MIN
        elif val < 0.66: img = stock.VOLUME_MED
        else: img = stock.VOLUME_MAX
        image.set_from_stock(img, SIZE)

        device.volume = val
        config.set("memory", "volume", str(slider.get_value()))

class StopAfterMenu(gtk.Menu):
    def __init__(self, watcher, player):
        gtk.Menu.__init__(self)
        self.__item = gtk.CheckMenuItem(_("Stop after this song"))
        self.__item.set_active(False)
        self.append(self.__item)

        watcher.connect('paused', self.__paused)
        watcher.connect('song-ended', self.__ended, player)
        
        self.__item.show()

    def __paused(self, watcher):
        self.active = False

    def __ended(self, watcher, song, stopped, player):
        if stopped: self.active = False
        elif self.active: player.paused = True

    def __get_active(self): return self.__item.get_active()
    def __set_active(self, v): return self.__item.set_active(v)
    active = property(__get_active, __set_active)

class PlayControls(gtk.VBox):
    def __init__(self, watcher, player):
        gtk.VBox.__init__(self, spacing=3)
        hbox = gtk.HBox(spacing=3)
        prev = gtk.Button()
        prev.add(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PREVIOUS, SIZE))
        hbox.pack_start(prev)

        play = gtk.ToggleButton()
        play.add(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, SIZE))
        hbox.pack_start(play)
        safter = StopAfterMenu(watcher, player)

        next = gtk.Button()
        next.add(gtk.image_new_from_stock(gtk.STOCK_MEDIA_NEXT, SIZE))
        hbox.pack_start(next)

        self.pack_start(hbox, expand=False, fill=False)

        hbox = gtk.HBox(spacing=3)
        self.volume = Volume(player)
        hbox.pack_start(self.volume, expand=False)
        hbox.pack_start(SeekBar(watcher, player))
        self.pack_start(hbox, expand=False, fill=False)

        prev.connect_object('clicked', self.__previous, player)
        play.connect('toggled', self.__playpause, watcher, player)
        play.connect('button-press-event', self.__play_button_press, safter)
        play.connect_object('popup-menu', self.__popup, safter)
        next.connect_object('clicked', self.__next, player)
        watcher.connect('song-started', self.__song_started, next)
        watcher.connect_object('paused', play.set_active, False)
        watcher.connect_object('unpaused', play.set_active, True)
        self.show_all()

    def __play_button_press(self, activator, event, safter):
        if event.button == 3:
            return self.__popup(safter, event.button, event.time)
            
    def __popup(self, safter, button=3, time=None):
        time = time or gtk.get_current_event_time()
        safter.popup(None, None, None, button, time)
        return True

    def __song_started(self, watcher, song, next):
        next.set_sensitive(bool(song))

    def __playpause(self, button, watcher, player):
        if button.get_active() and player.song is None:
            player.reset()
        else: player.paused = not button.get_active()

    def __previous(self, player): player.previous()
    def __next(self, player): player.next()
