# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject, gtk
import util
from qltk.sliderbutton import HSlider

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

        gobject.timeout_add(1000, self.__check_time, player)
        watcher.connect('song-started', self.__song_changed, l)

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
        if not (self.__lock or player.paused):
            position = player.get_position() // 1000
            if (not self.__seekable and
                position > self.scale.get_adjustment().upper):
                self.scale.set_range(0, position)
            self.scale.set_value(position)
        return True

    def __update_time(self, scale, timer):
        timer.set_text(util.format_time(scale.get_value()))

    def __song_changed(self, watcher, song, label):
        if song:
            length = song["~#length"]
            if length <= 0:
                self.scale.set_range(0, 1)
                self.__seekable = False
            else:
                self.scale.set_range(0, length)
                self.__seekable = True
        else:
            self.scale.set_range(0, 1)
            self.__seekable = False
