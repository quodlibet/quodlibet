# Copyright 2006 Joe Wreschnig, 2010 Christoph Reiter
#           2016, 2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet import app
from quodlibet import qltk
from quodlibet.plugins.songshelpers import any_song, has_bookmark
from quodlibet.qltk.bookmarks import EditBookmarks
from quodlibet.qltk.x import SeparatorMenuItem
from quodlibet.qltk import Icons
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class Bookmarks(SongsMenuPlugin):
    PLUGIN_ID = "Go to Bookmark"
    PLUGIN_NAME = _(u"Go to Bookmark")
    PLUGIN_DESC = _("Manages bookmarks in the selected files.")
    PLUGIN_ICON = Icons.GO_JUMP

    plugin_handles = any_song(has_bookmark)

    def __init__(self, songs, *args, **kwargs):
        super(Bookmarks, self).__init__(songs, *args, **kwargs)
        self.__menu = Gtk.Menu()
        self.__create_children(self.__menu, songs)
        self.set_submenu(self.__menu)

    class FakePlayer(object):
        def __init__(self, song):
            self.song = song

        def seek(self, time):
            if app.player.go_to(self.song._song, explicit=True):
                app.player.seek(time)

        def get_position(self, *args):
            return 0

    def __create_children(self, menu, songs):
        self.__remove_children(menu)
        for song in songs:
            marks = song.bookmarks
            if marks:
                fake_player = self.FakePlayer(song)

                song_item = Gtk.MenuItem(song.comma("title"))
                song_menu = Gtk.Menu()
                song_item.set_submenu(song_menu)
                menu.append(song_item)

                items = qltk.bookmarks.MenuItems(marks, fake_player, True)
                for item in items:
                    song_menu.append(item)

                song_menu.append(SeparatorMenuItem())
                i = qltk.MenuItem(_(u"_Edit Bookmarks…"), Icons.EDIT)

                def edit_bookmarks_cb(menu_item):
                    window = EditBookmarks(self.plugin_window, app.library,
                                           fake_player)
                    window.show()
                i.connect('activate', edit_bookmarks_cb)
                song_menu.append(i)

        if menu.get_active() is None:
            no_marks = Gtk.MenuItem(_("No Bookmarks"))
            no_marks.set_sensitive(False)
            menu.append(no_marks)

        menu.show_all()

    def __remove_children(self, menu):
        for child in menu.get_children():
            menu.remove(child)

    def plugin_songs(self, songs):
        pass
