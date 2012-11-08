# -*- coding: utf-8 -*-
# Copyright 2004-2011 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Christoph Reiter, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import random

import gtk
import gobject

from quodlibet import config
from quodlibet import const
from quodlibet import qltk

from quodlibet.browsers._base import Browser
from quodlibet.parse import Query
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.x import Alignment

QUERIES = os.path.join(const.USERDIR, "lists", "queries")

# A browser that the user only interacts with indirectly, via the
# Filter menu. The VBox remains empty.
class EmptyBar(gtk.VBox, Browser):
    __gsignals__ = Browser.__gsignals__

    name = _("Disable Browser")
    accelerated_name = _("_Disable Browser")
    priority = 0
    in_menu = False

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
        else: return True

    def filter_text(self, text):
        self._text = text
        self.activate()

    def __query(self, text, library, window, player):
        self.filter_text(text)

    def save(self):
        config.set("browsers", "query_text", self._text.encode('utf-8'))

    def restore(self, activate=True):
        try:
            text = config.get("browsers", "query_text")
        except:
            return

        if activate:
            self.filter_text(text)
        else:
            self._text = text

    def finalize(self, restore):
        config.set("browsers", "query_text", "")

    def _get_songs(self):
        try: self._filter = Query(self._text, star=SongList.star).search
        except Query.error: pass
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
            gobject.idle_add(self.emit, 'songs-selected', songs, None)

    def can_filter_text(self):
        return True

    def unfilter(self):
        self.filter_text("")

class LimitSearchBar(SearchBarBox):

    class Limit(gtk.HBox):
        def __init__(self):
            super(LimitSearchBar.Limit, self).__init__(spacing=3)
            label = gtk.Label(_("_Limit:"))
            self.pack_start(label)

            self.__limit = limit = gtk.SpinButton()
            limit.set_numeric(True)
            limit.set_range(0, 99999)
            limit.set_increments(5, 50)
            label.set_mnemonic_widget(limit)
            label.set_use_underline(True)
            self.pack_start(limit)

            self.__weight = gtk.CheckButton(_("_Weight"))
            self.pack_start(self.__weight)
            map(lambda w: w.show(), self.get_children())

        def limit(self, songs):
            limit = self.__limit.get_value_as_int()
            if not limit or len(songs) < limit: return songs
            else:
                if self.__weight.get_active():
                    def choose(r1, r2):
                        if r1 or r2: return cmp(random.random(), r1/(r1+r2))
                        else: return random.randint(-1, 1)
                    def rating(song):
                        return song("~#rating")
                    songs.sort(cmp=choose, key=rating)
                else: random.shuffle(songs)
                return songs[:limit]

    def __init__(self, *args, **kwargs):
        super(LimitSearchBar, self).__init__(*args, **kwargs)
        self.__limit = self.Limit()
        self.__sep = gtk.VSeparator()
        self.pack_start(self.__sep, expand=False)
        self.reorder_child(self.__sep, 0)
        self.pack_start(self.__limit, expand=False)
        self.reorder_child(self.__limit, 0)
        self.pack_start(gtk.HSeparator(), expand=False)
        self.__limit.set_no_show_all(True)
        self.__sep.set_no_show_all(True)

    def limit(self, songs):
        return self.__limit.limit(songs)

    def Menu(self, menu):
        sep = gtk.SeparatorMenuItem()
        menu.prepend(sep)
        item = gtk.CheckMenuItem(_("_Limit Results"))
        menu.prepend(item)
        item.set_active(self.__limit.get_property('visible'))
        item.connect('toggled', self.__showhide_limit)
        item.show()
        sep.show()

    def __showhide_limit(self, button):
        if button.get_active():
            self.__limit.show()
            self.__sep.show()
        else:
            self.__limit.hide()
            self.__sep.hide()

# Like EmptyBar, but the user can also enter a query manually. This
# is QL's default browser. EmptyBar handles all the GObject stuff.
class SearchBar(EmptyBar):

    name = _("Search Library")
    accelerated_name = _("_Search Library")
    priority = 1
    in_menu = True

    def __init__(self, library, main, limit=True):
        super(SearchBar, self).__init__(library, main)
        self.set_spacing(6)

        completion = LibraryTagCompletion(library.librarian)
        self.accelerators = gtk.AccelGroup()
        if limit:
            self._search_bar = LimitSearchBar(completion=completion,
                                              accel_group=self.accelerators)
        else:
            self._search_bar = SearchBarBox(completion=completion,
                                            accel_group=self.accelerators)
        self._search_bar.connect('query-changed', self.__text_parse)

        def focus(widget, *args):
            qltk.get_top_parent(widget).songlist.grab_focus()
        self._search_bar.connect('focus-out', focus)

        self.connect('destroy', self.__destroy)
        if main:
            align = Alignment(self._search_bar, left=3, right=3, top=3)
        else:
            align = Alignment(self._search_bar)
        align.show()
        self.pack_start(align, expand=False)
        self.show()

    def __destroy(self, *args):
        self._search_bar = None

    def activate(self):
        songs = self._get_songs()
        if songs is not None and self._search_bar:
            songs = self._search_bar.limit(songs)
            gobject.idle_add(self.emit, 'songs-selected', songs, None)

    def __text_parse(self, bar, text):
        self._text = text
        self.activate()

    def filter_text(self, text):
        self._text = text
        self._search_bar.set_text(text)
        self.activate()

browsers = [EmptyBar, SearchBar]
