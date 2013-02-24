# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.tags import MACHINE_TAGS
from quodlibet.util import build_filter_query
from quodlibet.qltk import Window


class SelectionWindow(Window):
    def __init__(self, filters, browser, parent=None):
        super(SelectionWindow, self).__init__()
        self.set_border_width(10)
        self.set_title(FilterAll.PLUGIN_NAME)
        self.set_default_size(200, 250)
        self.set_transient_for(parent)

        model = gtk.ListStore(bool, str, str)
        for key, value in sorted(filters.items()):
            model.append(row=[False, key, value])

        toggle = gtk.CellRendererToggle()
        toggle.connect("toggled", self.__toggeled, model, browser)
        text = gtk.CellRendererText()

        toggle_column = gtk.TreeViewColumn("", toggle, active=0)
        column = gtk.TreeViewColumn("Tag", text, text=1)

        view = gtk.TreeView(model)
        view.append_column(toggle_column)
        view.append_column(column)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)

        buttons = gtk.HButtonBox()
        buttons.set_spacing(6)
        buttons.set_layout(gtk.BUTTONBOX_END)
        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        close.connect('clicked', lambda *x: self.destroy())
        buttons.pack_start(close)

        box = gtk.VBox(spacing=12)
        box.pack_start(sw)
        box.pack_start(buttons, expand=False)

        self.add(box)

        self.show_all()

    def __filter(self, model, browser):
        selected = {}
        for row in model:
            sel, key, value = row
            if sel:
                selected[key] = value

        joined = ", ".join(sorted(selected.values()))
        if len(selected) >= 2:
            joined = "&(%s)" % joined

        browser.filter_text(joined)

    def __toggeled(self, render, path, model, browser):
        model[path][0] = not model[path][0]
        self.__filter(model, browser)


class FilterAll(SongsMenuPlugin):
    PLUGIN_ID = "FilterAll"
    PLUGIN_NAME = _("Filter on any tag")
    PLUGIN_DESC = _("Create a search query based on "
                    "tags of the selected songs")
    PLUGIN_ICON = 'gtk-index'

    def plugin_songs(self, songs):
        browser = self.plugin_window.browser
        if not browser.can_filter_text():
            return

        keys = set()
        for song in songs:
            keys.update(song.realkeys())
        keys.difference_update(MACHINE_TAGS)

        filters = {}
        for key in keys:
            values = set()
            for song in songs:
                values.update(song.list(key))
            filters[key] = build_filter_query(key, values)

        SelectionWindow(filters, browser, parent=self.plugin_window)
