# -*- coding: utf-8 -*-
# Copyright 2018 Peter Strulo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import operator
from itertools import count
from functools import reduce

from gi.repository import Gtk

from quodlibet import _
from quodlibet.browsers.search import SearchBar
from quodlibet.qltk import Align
from quodlibet.query import Query


class MultiQueryBrowser(SearchBar):
    """A browser in which multiple queries are parsed
    and used to filter results
    """

    name = _("MultiQuery")
    accelerated_name = _("_MultiQuery")
    keys = ["MultiQuery"]
    priority = 0

    def __init__(self, library):
        super().__init__(library)
        self._sb_box._entry.connect('activate', self.add_list_query)

        self._list_box = lb = Gtk.ListBox()

        align = Align(lb, left=6, right=6, top=6)
        align.show_all()
        self.pack_start(align, False, True, 0)

    def add_list_query(self, _):
        q = ListQuery(self._get_text(), self.activate)
        q.show()
        self._list_box.add(q)
        self._set_text("")

    def _get_songs(self):
        # Gtk.ListBox doesn't seem to have a get_rows method?
        queries = []
        for i in count():
            lq = self._list_box.get_row_at_index(i)
            if lq is None:
                break
            queries.append(lq.query)

        if len(queries) == 0:
            return self._library
        self._query = reduce(operator.and_, queries)
        return self._query.filter(self._library) if self._query else None


class ListQuery(Gtk.ListBoxRow):
    """A ListBoxRow representing a query"""

    def __init__(self, string, changed_callback):
        super().__init__(activatable=False, selectable=False)

        self.changed_callback = changed_callback
        self.query = Query(string)

        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(string, halign=Gtk.Align.START, margin=3),
                        True, True, 0)
        btn = Gtk.Button.new_from_icon_name("window-close",
                                            Gtk.IconSize.BUTTON)
        btn.connect('clicked', self.remove)
        hbox.pack_start(btn, False, True, 0)
        self.add(hbox)
        self.show_all()

    def remove(self, _):
        self.destroy()
        self.changed_callback()


browsers = [MultiQueryBrowser]
