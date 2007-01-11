# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk

import stock

from qltk.delete import DeleteDialog
from qltk.information import Information
from qltk.properties import SongProperties

class SongsMenu(gtk.Menu):
    __accels = gtk.AccelGroup()

    def __init__(self, library, songs, plugins=True, playlists=True,
                 queue=True, devices=True, remove=True, delete=False,
                 edit=True, accels=None):
        super(SongsMenu, self).__init__()

        # The library may actually be a librarian; if it is, use it,
        # otherwise find the real librarian.
        librarian = getattr(library, 'librarian', library)

        if plugins:
            submenu = self.plugins.Menu(librarian, self, songs)
            if submenu is not None:
                b = gtk.ImageMenuItem(stock.PLUGINS)
                self.append(b)
                b.set_submenu(submenu)
                self.append(gtk.SeparatorMenuItem())

        in_lib = True
        can_add = True
        is_file = True
        for song in songs:
            if song not in library: in_lib = False
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

        if devices and browsers.media.MediaDevices in browsers.browsers:
            import browsers
            try: submenu = browsers.media.Menu(songs, library)
            except AttributeError: pass
            else:
                b = gtk.ImageMenuItem(stock.DEVICES)
                b.set_sensitive(can_add and len(submenu) > 0)
                b.set_submenu(submenu)
                self.append(b)

        if remove or delete or edit:
            self.separate()

        if remove:
            b = gtk.ImageMenuItem(stock.REMOVE)
            if callable(remove):
                b.connect_object('activate', remove, songs)
            else:
                b.connect_object('activate', library.remove, songs)
                b.set_sensitive(in_lib)
            self.append(b)

        if delete:
            b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
            if callable(delete):
                b.connect_object('activate', delete, songs)
            else:
                b.connect('activate', self.__delete, songs, librarian)
                b.set_sensitive(is_file)
            self.append(b)

        if edit:
            b = gtk.ImageMenuItem(stock.EDIT_TAGS)
            if accels is not None:
                key, val = gtk.accelerator_parse("<alt>Return")
                b.add_accelerator(
                    'activate', accels, key, val, gtk.ACCEL_VISIBLE)
            b.connect_object('activate', SongProperties, librarian, songs)
            self.append(b)

            b = gtk.ImageMenuItem(gtk.STOCK_INFO)
            if accels is not None:
                b.add_accelerator('activate', accels, ord('I'),
                                  gtk.gdk.CONTROL_MASK, gtk.ACCEL_VISIBLE)
            b.connect_object('activate', Information, librarian, songs)
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

    def __remove(self, item, songs, library):
        library.remove(songs)

    def __enqueue(self, item, songs):
        songs = filter(lambda s: s.can_add, songs)
        if songs:
            from widgets import main
            main.playlist.enqueue(songs)

    def __delete(self, item, songs, library):
        files = [song["~filename"] for song in songs]
        d = DeleteDialog(None, files)
        removed = dict.fromkeys(d.run())
        d.destroy()
        removed = filter(lambda s: s["~filename"] in removed, songs)
        if removed:
            try: library.librarian.remove(removed)
            except AttributeError:
                library.remove(removed)
