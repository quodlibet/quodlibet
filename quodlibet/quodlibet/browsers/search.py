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
        self.__main = bool(player)
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
                if self.__main: self.save()

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

class Limit(gtk.HBox):
    def __init__(self):
        super(Limit, self).__init__(spacing=3)
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

class BoxSearchBar(gtk.HBox):
    def __init__(self, library, limit=False, button=True, completion=None):
        super(BoxSearchBar, self).__init__(spacing=6)

        self.__limit = None
        self.callback = None
        self.__refill_id = None

        if limit: self.__limit = Limit()

        combo = ComboBoxEntrySave(QUERIES, count=8,
            validator=Query.is_valid_color, title=_("Saved Searches"),
            edit_title=_("Edit saved searches..."))
        if not completion:
            completion = LibraryTagCompletion(library.librarian)
        combo.child.set_completion(completion)

        self.set_text = combo.child.set_text

        combo.child.connect('activate', self.__text_parse)
        combo.child.connect('activate', self.__save_search)
        combo.child.connect('focus-out-event', self.__save_search)
        combo.child.connect('changed', self.__test_filter)
        combo.child.connect('backspace', self.__test_filter)
        combo.child.connect('realize', lambda w: w.grab_focus())

        label = gtk.Label(_("_Search:"))
        label.set_use_underline(True)
        label.connect('mnemonic-activate', self._mnemonic_activate)
        label.set_mnemonic_widget(combo.child)

        if button:
            search = gtk.Button()
            search.connect_object('clicked', self.__text_parse, combo.child)
            hb = gtk.HBox(spacing=3)
            hb.pack_start(gtk.image_new_from_stock(
                gtk.STOCK_FIND, gtk.ICON_SIZE_MENU), expand=False)
            hb.pack_start(gtk.Label(_("Search")))
            search.add(hb)
            search.set_tooltip_text(_("Search your library"))

        if self.__limit:
            combo.child.connect('populate-popup', self.__menu, self.__limit)
            self.pack_start(self.__limit, expand=False)

        self.pack_start(label, expand=False)

        combo_hb = gtk.HBox()
        combo_hb.pack_start(combo)
        combo.pack_clear_button(combo_hb)

        self.pack_start(combo_hb)
        if button:
            self.pack_start(search, expand=False)

        self.__combo = combo
        self.show_all()

        if self.__limit: self.__limit.hide()

    def limit_songs(self, songs):
        if self.__limit and self.__limit.get_property('visible'):
            return self.__limit.limit(songs)
        else:
            return songs

    def __showhide_limit(self, button, hb):
        if button.get_active(): hb.show()
        else: hb.hide()

    def __menu(self, entry, menu, hb):
        sep = gtk.SeparatorMenuItem()
        menu.prepend(sep)
        item = gtk.CheckMenuItem(_("_Limit Results"))
        menu.prepend(item)
        item.set_active(hb.get_property('visible'))
        item.connect('toggled', self.__showhide_limit, hb)
        item.show()
        sep.show()

    def _mnemonic_activate(self, label, group_cycling):
        # If our mnemonic widget already has the focus, switch to
        # the song list instead. (#254)
        widget = label.get_mnemonic_widget()
        if widget.is_focus():
            qltk.get_top_parent(widget).songlist.grab_focus()
            return True

    def __text_parse(self, entry):
        self.__refill_id = None
        text = entry.get_text()
        if self.callback:
            self.callback(text)
        return False

    def __save_search(self, entry, *args):
        text = entry.get_text().decode('utf-8')
        if args and not config.getboolean('settings', 'eager_search'):
            # Called from 'focus-out-event' signal
            return
        if text and Query.is_parsable(text):
            self.__combo.prepend_text(text.strip())
            self.__combo.write()

    def __test_filter(self, textbox):
        text = textbox.get_text().decode('utf-8')
        if config.getboolean('settings', 'eager_search'):
            if self.__refill_id is not None:
                gobject.source_remove(self.__refill_id)
                self.__refill_id = None
            if Query.is_parsable(text):
                self.__refill_id = gobject.timeout_add(
                        500, self.__text_parse, textbox)

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
        self._search_bar = BoxSearchBar(library, limit)
        self._search_bar.callback = self._text_parse
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
                songs = self._search_bar.limit_songs(songs)
                self.emit('songs-selected', songs, None)
                if self.__save: self.save()

    def _text_parse(self, text):
        if Query.is_parsable(text):
            self._text = text.decode('utf-8')
            self.activate()

    def set_text(self, text):
        super(SearchBar, self).set_text(text)
        self._search_bar.set_text(text)

browsers = [EmptyBar, SearchBar]
