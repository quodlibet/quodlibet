# -*- coding: utf-8 -*-
# Copyright 2004-2010 Joe Wreschnig, Michael Urman, Iñigo Serna,
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
from quodlibet.qltk.cbes import ComboBoxEntrySave
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.searchbar import SearchBarBox

QUERIES = os.path.join(const.USERDIR, "lists", "queries")

# A browser that the user only interacts with indirectly, via the
# Filter menu. The VBox remains empty.
class EmptyBar(gtk.VBox, Browser):
    __gsignals__ = Browser.__gsignals__

    name = _("Disable Browser")
    accelerated_name = _("_Disable Browser")
    priority = 0
    in_menu = False

    def __init__(self, library, player):
        super(EmptyBar, self).__init__()
        # When _text is None, calls to activate are ignored. This is to
        # avoid the song list changing when the user switches browses and
        # then refreshes.
        self._text = None
        self._filter = None
        self._library = library
        self.commands = {"query": self.__query}
        self.connect('destroy', self.__destroy)

    def __destroy(self, *args):
        del self.commands

    def dynamic(self, song):
        if self._filter is not None:
            return self._filter(song)
        else: return True

    def set_text(self, text):
        if isinstance(text, str): text = text.decode('utf-8')
        self._text = text

    status = property(lambda s: s._text)

    def __query(self, text, library, window, player):
        self.set_text(text)
        self.activate()

    def save(self):
        if self._text is not None:
            config.set("browsers", "query_text", self._text.encode('utf-8'))

    def restore(self):
        try: self.set_text(config.get("browsers", "query_text"))
        except: pass

    def finalize(self, restore):
        config.set("browsers", "query_text", "")

    def activate(self):
        if self._text is not None:
            try: self._filter = Query(self._text, star=SongList.star).search
            except Query.error: pass
            else:
                songs = filter(self._filter, self._library)
                self.emit('songs-selected', songs, None)

    def can_filter(self, key): return True

    def filter(self, key, values):
        if not values: return
        if key.startswith("~#"):
            nheader = key[2:]
            queries = ["#(%s = %s)" % (nheader, i) for i in values]
            if len(queries) > 1: self.set_text(u"|(%s)" % ", ".join(queries))
            else: self.set_text(queries[0])
        else:
            text = ", ".join(
                ["'%s'c" % v.replace("\\", "\\\\").replace("'", "\\'")
                 for v in values])
            if len(values) == 1: self.set_text(u"%s = %s" % (key, text))
            else: self.set_text(u"%s = |(%s)" % (key, text))
        self.activate()

    def unfilter(self):
        self.set_text("")
        self.activate()

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

    def __init__(self, library, player, limit=True):
        super(SearchBar, self).__init__(library, player)
        self.set_spacing(6)
        self.__save = bool(player)

        completion = LibraryTagCompletion(library.librarian)
        self.accelerators = gtk.AccelGroup()
        if limit:
            self._search_bar = LimitSearchBar(completion=completion,
                                              accel_group=self.accelerators)
        else:
            self._search_bar = SearchBarBox(completion=completion,
                                            accel_group=self.accelerators)
        self._search_bar.connect('query-changed', self._text_parse)

        def focus(widget, *args):
            qltk.get_top_parent(widget).songlist.grab_focus()
        self._search_bar.connect('focus-out', focus)

        self.connect('destroy', self.__destroy)
        self.pack_start(self._search_bar, expand=False)
        self.show()

    def __destroy(self, *args):
        self._search_bar = None

    def activate(self):
        if self._text is not None:
            try:
                self._filter = Query(self._text, star=SongList.star).search
            except Query.error:
                pass
            else:
                songs = filter(self._filter, self._library.itervalues())
                songs = self._search_bar.limit(songs)
                self.emit('songs-selected', songs, None)

    def _text_parse(self, bar, text):
        self._text = text.decode('utf-8')
        self.activate()

    def set_text(self, text):
        super(SearchBar, self).set_text(text)
        self._search_bar.set_text(text)

browsers = [EmptyBar, SearchBar]
