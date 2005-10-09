# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject, gtk
import config

from widgets import PlayList, PlaylistWindow
from browsers.base import Browser
from library import library

class PlaylistBar(Browser, gtk.HBox):
    __gsignals__ = Browser.__gsignals__
    background = False

    def __init__(self, main=True):
        gtk.HBox.__init__(self)
        Browser.__init__(self)
        combo = gtk.ComboBox(PlayList.lists_model())
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        self.pack_start(combo)

        edit = gtk.Button()
        refresh = gtk.Button()
        edit.add(gtk.image_new_from_stock(gtk.STOCK_EDIT, gtk.ICON_SIZE_MENU))
        refresh.add(gtk.image_new_from_stock(gtk.STOCK_REFRESH,
                                             gtk.ICON_SIZE_MENU))
        edit.set_sensitive(False)
        refresh.set_sensitive(False)
        self.pack_start(edit, expand=False)
        self.pack_start(refresh, expand=False)
        edit.connect('clicked', self.__edit_current, combo)
        combo.connect('changed', self.__list_selected, edit, refresh)
        refresh.connect_object(
            'clicked', self.__list_selected, combo, edit, refresh)

        tips = gtk.Tooltips()
        tips.set_tip(edit, _("Edit the current playlist"))
        tips.set_tip(refresh, _("Refresh the current playlist"))
        self.connect_object('destroy', combo.set_model, None)
        self.connect_object('destroy', gtk.Tooltips.destroy, tips)
        tips.enable()
        self.show_all()

    def save(self):
        combo = self.get_children()[0]
        active = combo.get_active()
        key = combo.get_model()[active][1]
        config.set("browsers", "playlist", key)

    def restore(self):
        try: key = config.get("browsers", "playlist")
        except Exception: self.get_children()[0].set_active(0)
        else:
            combo = self.get_children()[0]
            model = combo.get_model()
            def find_key(model, path, iter, key):
                if model[iter][1] == key:
                    combo.set_active(path[0])
                    return True
            model.foreach(find_key, key)

    def activate(self):
        self.__list_selected(*self.get_children())

    def __list_selected(self, combo, edit, refresh):
        active = combo.get_active()
        edit.set_sensitive(active > 0)
        refresh.set_sensitive(active > 0)
        if active == -1: return # Unset
        self.save()
        if active == 0:
            self.emit('songs-selected', library.values(), None)
        else:
            key = "~#playlist_" + combo.get_model()[active][1]
            songs = filter(lambda s: key in s, library.itervalues())
            self.emit('songs-selected', songs, key)

    def __edit_current(self, edit, combo):
        active = combo.get_active()
        if active > 0: PlaylistWindow(combo.get_model()[active][0])

gobject.type_register(PlaylistBar)

browsers = [(2, _("_Playlists"), PlaylistBar, False)]
