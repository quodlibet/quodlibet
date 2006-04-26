# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk

import stock

from library import library
from qltk.delete import DeleteDialog
from qltk.information import Information
from qltk.properties import SongProperties

class SongsMenu(gtk.Menu):
    __accels = gtk.AccelGroup()

    def __init__(self, watcher, songs, plugins=True, playlists=True,
                 queue=True, remove=True, delete=False, edit=True,
                 accels=None):
        super(SongsMenu, self).__init__()

        if plugins:
            submenu = self.plugins.Menu(watcher, self, songs)
            if submenu is not None:
                b = gtk.ImageMenuItem(stock.PLUGINS)
                self.append(b)
                b.set_submenu(submenu)
                self.append(gtk.SeparatorMenuItem())

        in_lib = True
        can_add = True
        is_file = True
        for song in songs:
            if song.get("~filename") not in library: in_lib = False
            if not song.can_add: can_add = False
            if not song.is_file: is_file = False

        self.separate()

        if playlists:
            # Needed here to avoid a circular import; most browsers use
            # a SongsMenu, but SongsMenu needs access to the playlist
            # browser for this item.
            import browsers
            try: submenu = browsers.playlists.Menu(songs)
            except AttributeError: pass
            else:
                b = gtk.ImageMenuItem(stock.PLAYLISTS)
                b.set_sensitive(can_add)
                b.set_submenu(submenu)
                self.append(b)
        if queue:
            b = gtk.ImageMenuItem(stock.ENQUEUE)
            b.connect('activate', self.__enqueue, songs)
            if accels is not None:
                b.add_accelerator(
                    'activate', accels, ord('Q'), 0, gtk.ACCEL_VISIBLE)
            self.append(b)
            b.set_sensitive(can_add)

        if remove:
            self.separate()
            b = gtk.ImageMenuItem(stock.REMOVE)
            b.connect('activate', self.__remove, songs, watcher)
            self.append(b)
            b.set_sensitive(in_lib)

        if delete:
            b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
            b.connect('activate', self.__delete, songs, watcher)
            self.append(b)
            b.set_sensitive(is_file)

        if edit:
            b = gtk.ImageMenuItem(stock.EDIT_TAGS)
            if accels is not None:
                key, val = gtk.accelerator_parse("<alt>Return")
                b.add_accelerator(
                    'activate', accels, key, val, gtk.ACCEL_VISIBLE)
            b.connect_object('activate', SongProperties, watcher, songs)
            self.append(b)

            b = gtk.ImageMenuItem(gtk.STOCK_INFO)
            if accels is not None:
                b.add_accelerator('activate', accels, ord('I'),
                                  gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
            b.connect_object('activate', Information, watcher, songs)
            self.append(b)

        self.connect_object('selection-done', gtk.Menu.destroy, self)

    def separate(self):
        if not self.get_children(): return
        elif not isinstance(self.get_children()[-1], gtk.SeparatorMenuItem):
            self.append(gtk.SeparatorMenuItem())

    def preseparate(self):
        if not self.get_children(): return
        elif not isinstance(self.get_children()[0], gtk.SeparatorMenuItem):
            self.prepend(gtk.SeparatorMenuItem())

    def __remove(self, item, songs, watcher):
        map(library.remove, songs)
        watcher.removed(songs)

    def __enqueue(self, item, songs):
        songs = filter(lambda s: s.can_add, songs)
        if songs:
            from widgets import main, watcher
            added = filter(library.add_song, songs)
            main.playlist.enqueue(songs)
            if added: watcher.added(added)

    def __delete(self, item, songs, watcher):
        files = [song["~filename"] for song in songs]
        d = DeleteDialog(None, files)
        removed = dict.fromkeys(d.run())
        d.destroy()
        removed = filter(lambda s: s["~filename"] in removed, songs)
        if removed:
            map(library.remove, removed)
            watcher.removed(removed)
