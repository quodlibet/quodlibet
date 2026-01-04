# Copyright 2012 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.util.tags import MACHINE_TAGS
from quodlibet.util import build_filter_query
from quodlibet.qltk import Window, Icons, Button


class SelectionWindow(Window):
    def __init__(self, filters, browser, parent=None):
        super().__init__()
        self.set_border_width(10)
        self.set_title(FilterAll.PLUGIN_NAME)
        self.set_default_size(200, 250)
        self.set_transient_for(parent)

        model = Gtk.ListStore(bool, str, str)
        for key, value in sorted(filters.items()):
            model.append(row=[False, key, value])

        toggle = Gtk.CellRendererToggle()
        toggle.connect("toggled", self.__toggeled, model, browser)
        text = Gtk.CellRendererText()

        toggle_column = Gtk.TreeViewColumn("", toggle, active=0)
        column = Gtk.TreeViewColumn(_("Tag"), text, text=1)

        view = Gtk.TreeView(model)
        view.append_column(toggle_column)
        view.append_column(column)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(view)

        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        buttons.set_spacing(6)
        buttons.set_layout(Gtk.ButtonBoxStyle.END)
        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        close.connect("clicked", lambda *x: self.destroy())
        buttons.prepend(close)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.prepend(sw)
        box.prepend(buttons)

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
            joined = f"&({joined})"

        browser.filter_text(joined)

    def __toggeled(self, render, path, model, browser):
        model[path][0] = not model[path][0]
        self.__filter(model, browser)


class FilterAll(SongsMenuPlugin):
    PLUGIN_ID = "FilterAll"
    PLUGIN_NAME = _("Filter on Any Tag")
    PLUGIN_DESC = _("Creates a search query based on tags of the selected songs.")
    PLUGIN_ICON = Icons.EDIT_FIND
    REQUIRES_ACTION = True

    def plugin_songs(self, songs):
        browser = self.plugin_window.browser
        if not browser.can_filter_text():
            return

        keys = {key for song in songs for key in song.realkeys()}
        keys.difference_update(MACHINE_TAGS)

        filters = {}
        for key in keys:
            values = set()
            for song in songs:
                values.update(song.list(key))
            filters[key] = build_filter_query(key, values)

        SelectionWindow(filters, browser, parent=self.plugin_window)
