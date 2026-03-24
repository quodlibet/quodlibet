# Copyright 2004-2022 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson, Nick Boultbee,
#           2018-2019 Peter Strulo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GLib

from quodlibet import app
from quodlibet import config
from quodlibet import qltk
from quodlibet import _
from quodlibet.browsers import Browser
from quodlibet.qltk import is_accel
from quodlibet.qltk.ccb import ConfigCheckMenuItem
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.menubutton import MenuButton
from quodlibet.qltk.searchbar import MultiSearchBarBox
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.x import SymbolicIconImage, Align
from quodlibet.qltk import Icons


class PreferencesButton(Gtk.HBox):
    def __init__(self, search_bar_box):
        super().__init__()
        menu = Gtk.Menu()

        limit_item = ConfigCheckMenuItem(
            _("_Limit Results"), "browsers", "search_limit", True
        )
        limit_item.connect("toggled", search_bar_box.toggle_limit_widgets)
        menu.append(limit_item)

        multi_item = ConfigCheckMenuItem(
            _("_Allow multiple queries"), "browsers", "multiple_queries", True
        )
        multi_item.connect("toggled", search_bar_box.toggle_multi)
        menu.append(multi_item)

        menu.show_all()

        button = MenuButton(
            SymbolicIconImage(Icons.OPEN_MENU, Gtk.IconSize.MENU), arrow=True
        )
        button.set_menu(menu)
        self.pack_start(button, True, True, 0)


class TrackList(Browser):
    name = _("Track List")
    accelerated_name = _("_Track List")
    keys = ["SearchBar", "TrackList"]
    priority = 1

    def pack(self, songpane):
        container = Gtk.VBox(spacing=6)
        container.pack_start(self, False, True, 0)
        container.pack_start(songpane, True, True, 0)
        return container

    def unpack(self, container, songpane):
        container.remove(songpane)
        container.remove(self)

    def __init__(self, library):
        super().__init__(spacing=6, orientation=Gtk.Orientation.VERTICAL)

        self._query = None
        self._library = library

        completion = LibraryTagCompletion(library.librarian)
        self.accelerators = Gtk.AccelGroup()

        show_limit = config.getboolean("browsers", "search_limit")
        show_multi = config.getboolean("browsers", "multiple_queries")
        sbb = MultiSearchBarBox(
            completion=completion,
            accel_group=self.accelerators,
            show_limit=show_limit,
            show_multi=show_multi,
        )

        sbb.connect("query-changed", self.__text_parse)
        sbb.connect("focus-out", self.__focus)
        sbb.connect("key-press-event", self.__sb_key_pressed)
        self._sb_box = sbb

        prefs = PreferencesButton(sbb)
        sbb.pack_start(prefs, False, True, 0)

        self.pack_start(Align(sbb, left=6, right=6), False, True, 0)
        self.pack_start(sbb.flow_box, False, True, 0)
        self.connect("destroy", self.__destroy)
        self.show_all()

    def _get_text(self):
        return self._sb_box.get_text()

    def _set_text(self, text):
        self._sb_box.set_text(text)

    def __destroy(self, *args):
        self._sb_box = None

    def __focus(self, widget, *args):
        qltk.get_top_parent(widget).songlist.grab_focus()

    def _get_songs(self):
        self._query = self._sb_box.get_query(SongList.star)
        return self._query.filter(self._library) if self._query else None

    def activate(self):
        songs = self._get_songs()
        if songs is not None:
            songs = self._sb_box.limit(songs)
            GLib.idle_add(self.songs_selected, songs)

    def __text_parse(self, bar, text):
        self.activate()

    def __sb_key_pressed(self, entry, event):
        if is_accel(event, "<Primary>Return") or is_accel(event, "<Primary>KP_Enter"):
            songs = app.window.songlist.get_songs()
            limit = config.getint("browsers", "searchbar_enqueue_limit")
            app.window.enqueue(songs, limit)
            return True
        return False

    def save(self):
        config.settext("browsers", "query_text", self._get_text())
        self._sb_box.save()

    def restore(self):
        text = config.gettext("browsers", "query_text")
        self._set_text(text)
        self._sb_box.load()

    def finalize(self, restore):
        config.set("browsers", "query_text", "")

    def can_filter_text(self):
        return True

    def filter_text(self, text):
        self._set_text(text)
        self.activate()

    def get_filter_text(self):
        return self._get_text()

    def unfilter(self):
        self.filter_text("")

    def active_filter(self, song):
        if self._query is not None:
            return self._query.search(song)
        return True


browsers = [TrackList]
