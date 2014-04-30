# -*- coding: utf-8 -*-
# Copyright 2004-2013 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, GLib

from quodlibet import config

from quodlibet.browsers._base import Browser
from quodlibet.parse import Query
from quodlibet.qltk.songlist import SongList


class EmptyBar(Gtk.VBox, Browser):
    """A browser that the user only interacts with indirectly, via the
    Filter menu. The VBox remains empty."""

    __gsignals__ = Browser.__gsignals__

    name = _("Disable Browser")
    accelerated_name = _("_Disable Browser")
    priority = 0
    in_menu = False

    def pack(self, songpane):
        container = Gtk.VBox(spacing=6)
        container.pack_start(self, False, True, 0)
        container.pack_start(songpane, True, True, 0)
        return container

    def unpack(self, container, songpane):
        container.remove(songpane)
        container.remove(self)

    def __init__(self, library, main):
        super(EmptyBar, self).__init__()
        self._text = ""
        self._filter = None
        self._library = library
        self.commands = {"query": self.__query}
        self.connect('destroy', self.__destroy)

    def __destroy(self, *args):
        del self.commands

    def active_filter(self, song):
        if self._filter is not None:
            return self._filter(song)
        else:
            return True

    def filter_text(self, text):
        self._text = text
        self.activate()

    def __query(self, text, library, window, player):
        self.filter_text(text)

    def save(self):
        config.set("browsers", "query_text", self._text.encode('utf-8'))

    def restore(self):
        try:
            text = config.get("browsers", "query_text")
        except Exception:
            return

        self._text = text

    def finalize(self, restore):
        config.set("browsers", "query_text", "")

    def _get_songs(self):
        try:
            self._filter = Query(self._text, star=SongList.star).search
        except Query.error:
            pass
        else:
            if Query.match_all(self._text):
                songs = self._library.values()
                self._filter = None
            else:
                songs = filter(self._filter, self._library)
            return songs

    def activate(self):
        songs = self._get_songs()
        if songs is not None:
            GLib.idle_add(self.emit, 'songs-selected', songs, None)

    def can_filter_text(self):
        return True

    def unfilter(self):
        self.filter_text("")


browsers = [EmptyBar]
