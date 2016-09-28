# -*- coding: utf-8 -*-
# Copyright 2004-2013 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk
from gi.repository import Pango
from senf import fsn2text

from quodlibet import _
from quodlibet.qltk.chooser import FolderChooser
from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.qltk.x import MenuItem, Button
from quodlibet.qltk import Icons
from quodlibet.util.path import unexpand, get_home_dir
from quodlibet.util.library import get_scan_dirs, set_scan_dirs
from quodlibet.util import connect_obj


def get_init_select_dir():
    scandirs = get_scan_dirs()
    if scandirs and os.path.isdir(scandirs[-1]):
        # start with last added directory
        return scandirs[-1]
    else:
        return get_home_dir()


class ScanBox(Gtk.HBox):
    """A box for editing the Library's scan directories"""
    def __init__(self):
        super(ScanBox, self).__init__(spacing=6)

        self.model = model = Gtk.ListStore(str)
        view = RCMHintedTreeView(model=model)
        view.set_fixed_height_mode(True)
        view.set_headers_visible(False)
        view.set_tooltip_text(_("Songs in the listed folders will be added "
                                "to the library during a library refresh"))
        menu = Gtk.Menu()
        remove_item = MenuItem(_("_Remove"), Icons.LIST_REMOVE)
        menu.append(remove_item)
        menu.show_all()
        view.connect('popup-menu', self.__popup, menu)
        connect_obj(remove_item, 'activate', self.__remove, view)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(view)
        sw.set_size_request(-1, max(sw.size_request().height, 80))

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)

        def cdf(column, cell, model, iter, data):
            row = model[iter]
            cell.set_property('text', unexpand(row[0]))

        column = Gtk.TreeViewColumn(None, render)
        column.set_cell_data_func(render, cdf)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        view.append_column(column)

        add = Button(_("_Add"), Icons.LIST_ADD)
        add.connect("clicked", self.__add)
        remove = Button(_("_Remove"), Icons.LIST_REMOVE)

        selection = view.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect("changed", self.__select_changed, remove)
        selection.emit("changed")

        connect_obj(remove, "clicked", self.__remove, view)

        vbox = Gtk.VBox(spacing=6)
        vbox.pack_start(add, False, True, 0)
        vbox.pack_start(remove, False, True, 0)

        self.pack_start(sw, True, True, 0)
        self.pack_start(vbox, False, True, 0)

        paths = map(fsn2text, get_scan_dirs())
        for path in paths:
            model.append(row=[path])

        for child in self.get_children():
            child.show_all()

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __select_changed(self, selection, remove_button):
        remove_button.set_sensitive(selection.count_selected_rows())

    def __save(self):
        set_scan_dirs([r[0] for r in self.model])

    def __remove(self, view):
        view.remove_selection()
        self.__save()

    def __add(self, *args):
        initial = get_init_select_dir()
        chooser = FolderChooser(self, _("Select Directories"), initial)
        fns = chooser.run()
        chooser.destroy()
        for fn in fns:
            self.model.append(row=[fn])
        self.__save()
