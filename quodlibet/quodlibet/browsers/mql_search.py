# -*- coding: utf-8 -*-
# Copyright 2012-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk, GLib

from quodlibet import _, get_user_dir
from quodlibet.browsers.search import SearchBar
from quodlibet.compat import listvalues

from quodlibet.qltk import Align
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.query.mql import Mql, ParseError
from quodlibet.util.collection import Collection
from quodlibet.util.dprint import print_d, print_w

QUERIES = os.path.join(get_user_dir(), "lists", "queries")

AGGREGATES = {
    'MB': ('~#filesize', 1024 * 1024),
    'GB': ('~#filesize', 1024 * 1024 * 1024),
    'MINS': ('~#length', 60),
    'HOURS': ('~#length', 60 * 60),
    'DAYS': ('~#filesize', 60 * 60 * 24),
}


class MqlSearchBarBox(SearchBarBox):
    pass


class MqlBrowser(SearchBar):

    def can_filter(self, key):
        return False

    name = _("MQL Browser")
    accelerated_name = _("_MQL Browser")
    keys = ["MqlSearch"]
    priority = 1
    in_menu = True

    def __init__(self, library):
        super(SearchBar, self).__init__()
        self.set_spacing(6)

        self._query = None
        self._library = library

        completion = LibraryTagCompletion(library.librarian)
        self.accelerators = Gtk.AccelGroup()

        sbb = MqlSearchBarBox(completion=completion,
                              query_class=Mql,
                              accel_group=self.accelerators)
        sbb.connect('query-changed', self._text_parse)
        sbb.connect('focus-out', self._focus)
        self.add_label(sbb)
        self._sb_box = sbb
        self.connect('destroy', self.__destroy)
        self.set_spacing(6)
        self.show_all()

    def add_label(self, sbb):
        align = Align(sbb, left=6, right=6, top=6)
        hbox = Gtk.HBox()
        label = Gtk.Label(label="MQL:")
        label.set_use_underline(True)
        label.set_mnemonic_widget(sbb)
        hbox.pack_start(label, False, False, 6)
        hbox.pack_start(align, True, True, 0)
        self.pack_start(hbox, True, True, 0)

    def _get_songs(self):
        collection = Collection()
        collection.songs = []
        text = self._get_text()
        if not text:
            print_d("empty search")
            collection.songs = listvalues(self._library)
            self._query = None
        else:
            try:
                tags = SongList.star
                print_d("Setting up MQL parser with %s" % tags)
                self._query = mql_query = Mql(text, star=tags)
                print_d(self._query)
                total = 0
                lim = mql_query.limit
                if lim is not None:
                    try:
                        tag, mul = AGGREGATES[lim.units]
                    except KeyError:
                        tag = lim.units
                        mul = 1
                    maxx = lim.value * mul
                for song in self._library:
                    if not self._query.search(song):
                        continue
                    elif lim is not None:
                        if lim.units == 'SONGS':
                            delta = 1
                            # Shortcut for cardinals
                            if total > maxx:
                                break
                        elif lim.units in AGGREGATES:
                            tag, mul = AGGREGATES[lim.units]
                            delta = song(tag)
                        else:
                            # Some cardinality stuff
                            vals = collection.list(tag)
                            new_vals = song.list(tag)
                            if not new_vals:
                                # Null values not included if in the LIMIT
                                continue
                            delta = len(set(new_vals) | set(vals)) - total
                            total = len(vals)
                        if total + delta <= maxx:
                            collection.songs.append(song)
                            collection.finalize()
                            total += delta
                            print_d("Total is now %d/%d %s(s)" %
                                    (total / mul, lim.value, lim.units))
                    else:
                        collection.songs.append(song)
                print_d("Chose %d songs from library of %d."
                        % (len(collection.songs), len(self._library)))
            except ParseError as e:
                print_w("Parse error: " + str(e))
        return collection.songs

    def __destroy(self, *args):
        self._search_bar = None

    def activate(self):
        songs = self._get_songs()
        if songs is not None:
            GLib.idle_add(self.emit, 'songs-selected', songs, None)

browsers = [MqlBrowser]
