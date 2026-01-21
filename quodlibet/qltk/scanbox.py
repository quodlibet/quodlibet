# Copyright 2004-2021 Joe Wreschnig, Michael Urman, Iñigo Serna,
#                     Steven Robertson, Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GLib, Pango

from quodlibet.qltk.msg import ConfirmationPrompt
from senf import fsn2text

from quodlibet import _, print_w, print_d, app, ngettext
from quodlibet.qltk.chooser import choose_folders, _get_chooser, _run_chooser
from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk.x import MenuItem, Button
from quodlibet.qltk import Icons, get_children
from quodlibet.util.path import unexpand
from quodlibet.util.library import get_scan_dirs, set_scan_dirs
from quodlibet.util import connect_obj, copool


class ScanBox(Gtk.Box):
    """A box for editing the Library's scan directories"""

    def __init__(self):
        super().__init__(spacing=6)

        self.model = model = ObjectStore()
        self.view = view = RCMHintedTreeView(model=model)
        view.set_fixed_height_mode(True)
        view.set_headers_visible(False)

        menu = Gtk.PopoverMenu()
        remove_item = MenuItem(_("_Remove"), Icons.LIST_REMOVE)
        menu.append(remove_item)
        menu.show_all()
        view.connect("popup-menu", self.__popup, menu)
        connect_obj(remove_item, "activate", self.__remove, view)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(view)
        sw.set_size_request(-1, 80)
        sw.set_tooltip_text(
            _(
                "Songs in the listed folders will be added "
                "to the library during a library refresh"
            )
        )
        render = Gtk.CellRendererText()
        render.set_property("ellipsize", Pango.EllipsizeMode.END)

        def cdf(column, cell, model, iter_, data):
            path = model.get_value(iter_)
            cell.set_property("text", fsn2text(unexpand(path)))

        column = Gtk.TreeViewColumn(None, render)
        column.set_cell_data_func(render, cdf)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        view.append_column(column)

        add = Button(_("_Add"), Icons.LIST_ADD)
        add.set_tooltip_text(_("The new directory will be scanned after adding"))
        add.connect("clicked", self.__add)
        remove = Button(_("_Remove"), Icons.LIST_REMOVE)
        remove.set_tooltip_text(
            _(
                "All songs in the selected directories "
                "will also be removed from the library"
            )
        )

        move = Button(_("_Move"), Icons.EDIT_REDO)
        move.connect("clicked", self.__move)
        move.set_tooltip_text(
            _(
                "Move a scan root (but not the files), "
                "migrating metadata for all included tracks."
            )
        )

        selection = view.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect("changed", self.__select_changed, remove, move)
        selection.emit("changed")

        connect_obj(remove, "clicked", self.__remove, view)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        vbox.append(add)
        vbox.append(remove)
        vbox.append(move)

        self.append(sw)
        self.append(vbox)

        for path in get_scan_dirs():
            model.append(row=[path])

        for child in get_children(self):
            child.show_all()

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, GLib.CURRENT_TIME)

    def __select_changed(self, selection, remove_button, move_button):
        remove_button.set_sensitive(selection.count_selected_rows())
        move_button.set_sensitive(selection.count_selected_rows() == 1)

    def __save(self):
        set_scan_dirs(list(self.model.itervalues()))

    def __remove(self, view) -> None:
        selection = self.view.get_selection()
        model, paths = selection.get_selected_rows()
        gone_dirs = [model[p][0] for p in paths or []]
        total = len(gone_dirs)
        if not total:
            return
        msg = (
            _("Remove {dir!r} and all its tracks?").format(dir=gone_dirs[0])
            if total == 1
            else _("Remove {n} library paths and their tracks?").format(n=total)
        )
        title = ngettext("Remove library path?", "Remove library paths?", total)
        prompt = ConfirmationPrompt(
            self, title, msg, _("Remove"), ok_button_icon=Icons.LIST_REMOVE
        )
        if prompt.run() == ConfirmationPrompt.RESPONSE_INVOKE:
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
        if not rows:
            return
        base_dir = rows[0][0]
        chooser = _get_chooser(_("Select This Directory"), _("_Cancel"))
        chooser.set_title(
            _("Select Actual / New Directory for {dir!r}").format(dir=base_dir)
        )
        chooser.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        chooser.set_local_only(True)
        chooser.set_select_multiple(False)
        results = _run_chooser(self, chooser)
        if not results:
            return
        new_dir = results[0]
        desc = _(
            "This will move QL metadata:\n\n"
            "{old!r} → {new!r}\n\n"
            "The audio files themselves are not moved by this.\n"
            "Nonetheless, a backup is recommended "
            "(including the Quod Libet 'songs' file)."
        ).format(old=base_dir, new=new_dir)
        title = _("Move scan root {dir!r}?").format(dir=base_dir)
        value = ConfirmationPrompt(
            self, title=title, description=desc, ok_button_text=_("OK, move it!")
        ).run()
        if value != ConfirmationPrompt.RESPONSE_INVOKE:
            print_d("User aborted")
            return
        print_d(f"Migrate from {base_dir} -> {new_dir}")
        copool.add(app.librarian.move_root, base_dir, new_dir)
        path = paths[0]
        self.model[path] = [new_dir]
        self.model.row_changed(path, rows[0].iter)
        self.__save()
