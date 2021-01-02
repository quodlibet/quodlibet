# Copyright 2004-2020 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk
from gi.repository import Pango
from senf import fsn2text

from quodlibet import _, print_w, print_d, app
from quodlibet.qltk.chooser import choose_folders, _get_chooser, _run_chooser
from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk.x import MenuItem, Button
from quodlibet.qltk import Icons
from quodlibet.util.path import unexpand
from quodlibet.util.library import get_scan_dirs, set_scan_dirs
from quodlibet.util import connect_obj, copool


class ScanBox(Gtk.HBox):
    """A box for editing the Library's scan directories"""

    def __init__(self):
        super().__init__(spacing=6)

        self.model = model = ObjectStore()
        self.view = view = RCMHintedTreeView(model=model)
        view.set_fixed_height_mode(True)
        view.set_headers_visible(False)

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
        sw.set_tooltip_text(_("Songs in the listed folders will be added "
                              "to the library during a library refresh"))
        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)

        def cdf(column, cell, model, iter_, data):
            path = model.get_value(iter_)
            cell.set_property('text', fsn2text(unexpand(path)))

        column = Gtk.TreeViewColumn(None, render)
        column.set_cell_data_func(render, cdf)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        view.append_column(column)

        add = Button(_("_Add"), Icons.LIST_ADD)
        add.connect("clicked", self.__add)
        remove = Button(_("_Remove"), Icons.LIST_REMOVE)
        move = Button(_("_Move"), Icons.EDIT_REDO)
        move.connect("clicked", self.__move)
        move.set_tooltip_text(_("Move a library directory, "
                                "migrating metadata for any included tracks."
                                "Ensure the files exist at the new location!"))

        selection = view.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect("changed", self.__select_changed, remove)
        selection.emit("changed")

        connect_obj(remove, "clicked", self.__remove, view)

        vbox = Gtk.VBox(spacing=6)
        vbox.pack_start(add, False, True, 0)
        vbox.pack_start(remove, False, True, 0)
        vbox.pack_start(move, False, True, 0)

        self.pack_start(sw, True, True, 0)
        self.pack_start(vbox, False, True, 0)

        for path in get_scan_dirs():
            model.append(row=[path])

        for child in self.get_children():
            child.show_all()

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __select_changed(self, selection, remove_button):
        remove_button.set_sensitive(selection.count_selected_rows())

    def __save(self):
        set_scan_dirs(list(self.model.itervalues()))

    def __remove(self, view):
        view.remove_selection()
        self.__save()

    def __add(self, *args):
        fns = choose_folders(self, _("Select Directories"), _("_Add Folders"))
        for fn in fns:
            self.model.append(row=[fn])
        self.__save()

    def __move(self, widget):
        selection = self.view.get_selection()
        model, paths = selection.get_selected_rows()
        rows = [model[p] for p in paths or []]
        if len(rows) > 1:
            print_w("Can't do multiple moves at once")
            return
        base_dir = rows[0][0]
        chooser = _get_chooser(_("Select New Directory"), _("_Cancel"))
        chooser.set_title(_("Select New Directory for {dir}").format(dir=base_dir))
        chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        chooser.set_local_only(True)
        chooser.set_select_multiple(False)
        results = _run_chooser(self, chooser)
        if not results:
            return
        new_dir = results[0]
        print_d(f"Migrate from {base_dir} -> {new_dir}")
        copool.add(app.librarian.move_root, base_dir, new_dir)
        path = paths[0]
        self.model[path] = [new_dir]
        self.model.row_changed(path, rows[0].iter)
        self.__save()
