# Copyright 2006 Joe Wreschnig, 2010 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import app
from quodlibet import qltk
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class Bookmarks(SongsMenuPlugin):
    PLUGIN_ID = "Go to Bookmark..."
    PLUGIN_NAME = _("Go to Bookmark...")
    PLUGIN_DESC = "List all bookmarks in the selected files."
    PLUGIN_ICON = Gtk.STOCK_JUMP_TO
    PLUGIN_VERSION = "0.4"

    def __init__(self, songs):
        super(Bookmarks, self).__init__(songs)
        self.__menu = Gtk.Menu()
        self.__menu.connect('map', self.__map, songs)
        self.__menu.connect('unmap', self.__unmap)
        self.set_submenu(self.__menu)

    class FakePlayer(object):
        def __init__(self, song):
            self.song = song

        def seek(self, time):
            if app.player.go_to(self.song._song, explicit=True):
                app.player.seek(time)

        get_position = lambda *x: 0

    def __map(self, menu, songs):
        for song in songs:
            marks = song.bookmarks
            if marks:
                fake_player = self.FakePlayer(song)

                song_item = Gtk.MenuItem(song.comma("title"))
                song_menu = Gtk.Menu()
                song_item.set_submenu(song_menu)
                menu.append(song_item)

                items = qltk.bookmarks.MenuItems(marks, fake_player, True)
                map(song_menu.append, items)

                song_menu.append(Gtk.SeparatorMenuItem())
                i = qltk.MenuItem(_("_Edit Bookmarks..."), Gtk.STOCK_EDIT)
                i.connect_object('activate',
                    qltk.bookmarks.EditBookmarks, None, app.library,
                    fake_player)
                song_menu.append(i)

        if menu.get_active() is None:
            no_marks = Gtk.MenuItem(_("No Bookmarks"))
            no_marks.set_sensitive(False)
            menu.append(no_marks)

        menu.show_all()

    def __unmap(self, menu):
        map(self.__menu.remove, self.__menu.get_children())

    def plugin_songs(self, songs):
        pass
