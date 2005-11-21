# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject, gtk
import const
import qltk
import parser
import config
from qltk.completion import LibraryTagCompletion

from browsers.base import Browser
from library import library

# A browser that the user only interacts with indirectly, via the
# Filter menu. The HBox remains empty.
class EmptyBar(gtk.HBox, Browser):
    __gsignals__ = Browser.__gsignals__

    def __init__(self, watcher, main):
        gtk.HBox.__init__(self)
        # When _text is None, calls to activate are ignored. This is to
        # avoid the song list changing when the user switches browses and
        # then refreshes.
        self._text = None
        self.__main = main

    def dynamic(self, song):
        if self._text is not None:
            from songlist import SongList
            try: return parser.parse(self._text, SongList.star).search(song)
            except parser.error: return True
        else: return True

    def set_text(self, text):
        if isinstance(text, str): text = text.decode('utf-8')
        self._text = text

    def save(self):
        config.set("browsers", "query_text", self._text.encode('utf-8'))

    def restore(self):
        try: self.set_text(config.get("browsers", "query_text"))
        except Exception: pass

    def activate(self):
        if self._text is not None:
            from songlist import SongList
            try: songs = library.query(self._text, star=SongList.star)
            except parser.error: pass
            else:
                self.emit('songs-selected', songs, None)
                if self.__main: self.save()

    def can_filter(self, key): return True

    def filter(self, key, values):
        if key.startswith("~#"):
            nheader = key[2:]
            queries = ["#(%s = %s)" % (nheader, i) for i in values]
            self.set_text("|(" + ", ".join(queries) + ")")
        else:
            text = ", ".join(
                ["'%s'c" % v.replace("\\", "\\\\").replace("'", "\\'")
                 for v in values])
            self.set_text(u"%s = |(%s)" % (key, text))
        self.activate()

gobject.type_register(EmptyBar)

# Like EmptyBar, but the user can also enter a query manually. This
# is QL's default browser. EmptyBar handles all the GObject stuff.
class SearchBar(EmptyBar):

    def __init__(self, watcher, main):
        EmptyBar.__init__(self, watcher, main)
        self.__save = main

        hb = gtk.HBox()
        lab = gtk.Label("_Limit:")
        lab.set_padding(3, 0)
        limit = gtk.SpinButton()
        limit.set_numeric(True)
        limit.set_range(0, 1000000)
        limit.set_increments(5, 50)
        lab.set_mnemonic_widget(limit)
        lab.set_use_underline(True)
        hb.pack_start(lab)
        hb.pack_start(limit)
        self.pack_start(hb, expand=False)

        tips = gtk.Tooltips()
        combo = qltk.ComboBoxEntrySave(
            const.QUERIES, model="searchbar", count=15)
        combo.child.set_completion(LibraryTagCompletion(watcher, library))
        clear = gtk.Button()
        clear.add(gtk.image_new_from_stock(gtk.STOCK_CLEAR,gtk.ICON_SIZE_MENU))
        tips.set_tip(clear, _("Clear search"))
        clear.connect_object('clicked', self.set_text, "")
                  
        search = gtk.Button()
        b = gtk.HBox(spacing=2)
        b.pack_start(gtk.image_new_from_stock(
            gtk.STOCK_FIND, gtk.ICON_SIZE_MENU))
        b.pack_start(gtk.Label(_("Search")))
        search.add(b)
        tips.set_tip(search, _("Search your library"))
        search.connect_object('clicked', self.__text_parse, combo.child)
        combo.child.connect('activate', self.__text_parse)
        limit.connect_object_after('activate', self.__text_parse, combo.child)
        combo.child.connect('changed', self.__test_filter)
        tips.enable()
        combo.child.connect('realize', lambda w: w.grab_focus())
        combo.child.connect('populate-popup', self.__menu, hb)
        self.connect_object('destroy', gtk.Tooltips.destroy, tips)
        self.pack_start(combo)
        self.pack_start(clear, expand=False)
        self.pack_start(search, expand=False)
        self.show_all()
        self._limit = limit
        hb.hide_all()

    def __menu(self, entry, menu, hb):
        sep = gtk.SeparatorMenuItem()
        menu.prepend(sep)
        item = gtk.CheckMenuItem(_("_Limit Results"))
        menu.prepend(item)
        item.set_active(hb.get_property('visible'))
        item.connect('toggled', self.__showhide_limit, hb)
        item.show(); sep.show()

    def __showhide_limit(self, button, hb):
        if button.get_active(): hb.show_all()
        else: hb.hide_all()

    def activate(self):
        if self._text is not None:
            from songlist import SongList
            try: songs = library.query(self._text, star=SongList.star)
            except parser.error: pass
            else:
                self.get_children()[1].prepend_text(self._text)
                val = self._limit.get_value_as_int()
                if (self._limit.get_property('visible') and
                    val and len(songs) > val):
                    import random
                    random.shuffle(songs)
                    songs = songs[:val]
                self.emit('songs-selected', songs, None)
                if self.__save: self.save()
                self.get_children()[1].write(const.QUERIES)

    def set_text(self, text):
        self.get_children()[1].child.set_text(text)
        if isinstance(text, str): text = text.decode('utf-8')
        self._text = text

    def __text_parse(self, entry):
        text = entry.get_text()
        if parser.is_parsable(text):
            self._text = text.decode('utf-8')
            self.activate()

    def __test_filter(self, textbox):
        if not config.getboolean('browsers', 'color'):
            textbox.modify_text(gtk.STATE_NORMAL, None)
            return
        text = textbox.get_text().decode('utf-8')
        color = parser.is_valid_color(text)
        if color and textbox.get_property('sensitive'):
            textbox.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(color))

browsers = [
    (0, _("_Disable Browser"), EmptyBar, False),
    (1, _("_Search Library"), SearchBar, True)
    ]
