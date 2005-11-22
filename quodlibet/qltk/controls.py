# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk

from qltk.volume import Volume
from qltk.seekbar import SeekBar

SIZE = gtk.ICON_SIZE_LARGE_TOOLBAR

class PlayControls(gtk.VBox):
    def __init__(self, watcher, player):
        gtk.VBox.__init__(self, spacing=3)
        self.set_border_width(3)

        hbox = gtk.HBox(spacing=3)
        prev = gtk.Button()
        prev.add(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PREVIOUS, SIZE))
        hbox.pack_start(prev)

        play = gtk.ToggleButton()
        play.add(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, SIZE))
        hbox.pack_start(play)

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
        next.connect_object('clicked', self.__next, player)
        watcher.connect('song-started', self.__song_started, next)
        watcher.connect_object('paused', play.set_active, False)
        watcher.connect_object('unpaused', play.set_active, True)

        self.show_all()

    def __song_started(self, watcher, song, next):
        next.set_sensitive(bool(song))

    def __playpause(self, button, watcher, player):
        if button.get_active() and player.song is None:
            player.reset()
            player.next()
        else: player.paused = not button.get_active()

    def __previous(self, player): player.previous()
    def __next(self, player): player.next()

