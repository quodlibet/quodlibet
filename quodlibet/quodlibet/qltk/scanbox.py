# -*- coding: utf-8 -*-
# Copyright 2004-2013 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk
import os
from gi.repository import Pango
from quodlibet import util, config, const
from quodlibet.qltk.chooser import FolderChooser
from quodlibet.qltk.views import RCMHintedTreeView


def get_init_select_dir():
    scandirs = util.split_scan_dirs(config.get("settings", "scan"))
    if scandirs and os.path.isdir(scandirs[-1]):
        # start with last added directory
        return scandirs[-1]
    else:
        return const.HOME


class ScanBox(Gtk.HBox):
    """A box for editing the Library's scan directories"""
    def __init__(self):
        super(ScanBox, self).__init__(spacing=6)

        self.model = model = Gtk.ListStore(str)
        view = RCMHintedTreeView(model)
        view.set_fixed_height_mode(True)
        view.set_headers_visible(False)
        view.set_tooltip_text(_("Songs in the listed folders will be added "
                                "to the library during a library refresh"))
        menu = Gtk.Menu()
        remove_item = Gtk.ImageMenuItem(Gtk.STOCK_REMOVE, use_stock=True)
        menu.append(remove_item)
        menu.show_all()
        view.connect('popup-menu', self.__popup, menu)
        remove_item.connect_object('activate', self.__remove, view)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(view)
        sw.set_size_request(-1, max(sw.size_request().height, 80))

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)

        def cdf(column, cell, model, iter, data):
            row = model[iter]
            cell.set_property('text', util.unexpand(row[0]))

        column = Gtk.TreeViewColumn(None, render)
        column.set_cell_data_func(render, cdf)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        view.append_column(column)

        add = Gtk.Button(stock=Gtk.STOCK_ADD)
        add.connect("clicked", self.__add)
        remove = Gtk.Button(stock=Gtk.STOCK_REMOVE)

        selection = view.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect("changed", self.__select_changed, remove)
        selection.emit("changed")

        remove.connect_object("clicked", self.__remove, view)

        vbox = Gtk.VBox(spacing=6)
        vbox.pack_start(add, False, True, 0)
        vbox.pack_start(remove, False, True, 0)

        self.pack_start(sw, True, True, 0)
        self.pack_start(vbox, False, True, 0)
        self.show_all()

        paths = util.split_scan_dirs(config.get("settings", "scan"))
        paths = map(util.fsdecode, paths)
        for path in paths:
            model.append(row=[path])

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __select_changed(self, selection, remove_button):
        remove_button.set_sensitive(selection.count_selected_rows())

    def __save(self):
        paths = map(util.fsencode, [r[0] for r in self.model])
        config.set("settings", "scan", ":".join(paths))

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
