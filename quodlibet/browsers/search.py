# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import random
import gobject, gtk
import const
import config

import qltk
from qltk.completion import LibraryTagCompletion
from qltk.cbes import ComboBoxEntrySave
from qltk.songlist import SongList
from qltk import Tooltips
from browsers._base import Browser
from library import library
from parse import Query

QUERIES = os.path.join(const.DIR, "lists", "queries")

# A browser that the user only interacts with indirectly, via the
# Filter menu. The HBox remains empty.
class EmptyBar(gtk.HBox, Browser):
    __gsignals__ = Browser.__gsignals__

    def __init__(self, watcher, player):
        gtk.HBox.__init__(self)
        # When _text is None, calls to activate are ignored. This is to
        # avoid the song list changing when the user switches browses and
        # then refreshes.
        self._text = None
        self.__main = bool(player)

    def dynamic(self, song):
        if self._text is not None:
            try: return Query(self._text, SongList.star).search(song)
            except Query.error: return True
        else: return True

    def set_text(self, text):
        if isinstance(text, str): text = text.decode('utf-8')
        self._text = text

    status = property(lambda s: s._text)

    def save(self):
        config.set("browsers", "query_text", self._text.encode('utf-8'))

    def restore(self):
        try: self.set_text(config.get("browsers", "query_text"))
        except: pass

    def activate(self):
        if self._text is not None:
            try: songs = library.query(self._text, star=SongList.star)
            except Query.error: pass
            else:
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

gobject.type_register(EmptyBar)

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
                songs = [(song.get("~#rating", 0.5), song) for song in songs]
                def choose((r1, s1), (r2, s2)):
                    if r1 or r2: return cmp(random.random(), r1/(r1+r2))
                    else: return random.randint(-1, 1)
                songs.sort(choose)
                songs = [song for (rating, song) in songs]
            else: random.shuffle(songs)
            return songs[:limit]
        
# Like EmptyBar, but the user can also enter a query manually. This
# is QL's default browser. EmptyBar handles all the GObject stuff.
class SearchBar(EmptyBar):

    def __init__(self, watcher, player):
        EmptyBar.__init__(self, watcher, player)
        self.__save = bool(player)
        self.set_spacing(12)

        self.__limit = Limit()
        self.pack_start(self.__limit, expand=False)

        hb2 = gtk.HBox(spacing=3)
        l = gtk.Label(_("_Search:"))
        l.connect('mnemonic-activate', self.__mnemonic_activate)
        tips = Tooltips(self)
        combo = ComboBoxEntrySave(
            QUERIES, model="searchbar", count=15)
        combo.child.set_completion(LibraryTagCompletion(watcher, library))
        l.set_mnemonic_widget(combo.child)
        l.set_use_underline(True)
        clear = gtk.Button()
        clear.add(gtk.image_new_from_stock(gtk.STOCK_CLEAR,gtk.ICON_SIZE_MENU))
        tips.set_tip(clear, _("Clear search"))
        clear.connect_object('clicked', self.set_text, "")

        search = gtk.Button()
        hb = gtk.HBox(spacing=3)
        hb.pack_start(gtk.image_new_from_stock(
            gtk.STOCK_FIND, gtk.ICON_SIZE_MENU), expand=False)
        hb.pack_start(gtk.Label(_("Search")))
        search.add(hb)
        tips.set_tip(search, _("Search your library"))
        search.connect_object('clicked', self.__text_parse, combo.child)
        combo.child.connect('activate', self.__text_parse)
        combo.child.connect('changed', self.__test_filter)
        combo.child.connect('realize', lambda w: w.grab_focus())
        combo.child.connect('populate-popup', self.__menu, self.__limit)
        hb2.pack_start(l, expand=False)
        hb3 = gtk.HBox()
        hb3.pack_start(combo)
        hb3.pack_start(clear, expand=False)
        hb3.pack_start(search, expand=False)
        hb2.pack_start(hb3)
        self.pack_start(hb2)
        self.show_all()
        self.__combo = combo
        self.__limit.hide()

    def __mnemonic_activate(self, label, group_cycling):
        # If our mnemonic widget already has the focus, switch to
        # the song list instead. (#254)
        widget = label.get_mnemonic_widget()
        if widget.is_focus():
            qltk.get_top_parent(widget).songlist.grab_focus()
            return True

    def __menu(self, entry, menu, hb):
        sep = gtk.SeparatorMenuItem()
        menu.prepend(sep)
        item = gtk.CheckMenuItem(_("_Limit Results"))
        menu.prepend(item)
        item.set_active(hb.get_property('visible'))
        item.connect('toggled', self.__showhide_limit, hb)
        item.show(); sep.show()

    def __showhide_limit(self, button, hb):
        if button.get_active(): hb.show()
        else: hb.hide()

    def activate(self):
        if self._text is not None:
            try: songs = library.query(self._text, star=SongList.star)
            except Query.error: pass
            else:
                self.__combo.prepend_text(self._text)
                if self.__limit.get_property('visible'):
                    songs = self.__limit.limit(songs)
                self.emit('songs-selected', songs, None)
                if self.__save: self.save()
                self.__combo.write(QUERIES)

    def set_text(self, text):
        self.__combo.child.set_text(text)
        if isinstance(text, str): text = text.decode('utf-8')
        self._text = text

    def __text_parse(self, entry):
        text = entry.get_text()
        if Query.is_parsable(text):
            self._text = text.decode('utf-8')
            self.activate()

    def __test_filter(self, textbox):
        if not config.getboolean('browsers', 'color'):
            textbox.modify_text(gtk.STATE_NORMAL, None)
            return
        text = textbox.get_text().decode('utf-8')
        color = Query.is_valid_color(text)
        if color and textbox.get_property('sensitive'):
            textbox.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse(color))

browsers = [
    (0, _("_Disable Browser"), EmptyBar, False),
    (1, _("_Search Library"), SearchBar, True)
    ]
