# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Pango

from quodlibet import util
from quodlibet import qltk
from quodlibet.qltk.views import RCMHintedTreeView


class ConfirmMaskedRemoval(qltk.Message):
    def __init__(self, parent):
        title = _("Are you sure you want to remove all songs?")
        description = _("The selected songs will be removed from the library.")

        super(ConfirmMaskedRemoval, self).__init__(
            Gtk.MessageType.WARNING, parent, title, description,
            Gtk.ButtonsType.NONE)

        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_DELETE, Gtk.ResponseType.YES)


class MaskedBox(Gtk.HBox):

    def __init__(self, library):
        super(MaskedBox, self).__init__(spacing=6)

        self.model = model = Gtk.ListStore(object)
        view = RCMHintedTreeView(model)
        view.set_fixed_height_mode(True)
        view.set_headers_visible(False)
        self.view = view

        menu = Gtk.Menu()
        unhide_item = qltk.MenuItem(_("Unhide"), Gtk.STOCK_ADD)
        unhide_item.connect_object('activate', self.__unhide, view, library)
        menu.append(unhide_item)

        remove_item = Gtk.ImageMenuItem(Gtk.STOCK_REMOVE, use_stock=True)
        remove_item.connect_object('activate', self.__remove, view, library)
        menu.append(remove_item)

        menu.show_all()
        view.connect('popup-menu', self.__popup, menu)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(view)
        sw.set_size_request(-1, max(sw.size_request().height, 80))

        def cdf(column, cell, model, iter, data):
            row = model[iter]
            cell.set_property('text', util.fsdecode(row[0]))

        def cdf_count(column, cell, model, iter, data):
            mount = model[iter][0]
            song_count = len(library.get_masked(mount))
            cell.set_property('text',
                _("%(song_count)d songs") % {"song_count": song_count})

        column = Gtk.TreeViewColumn(None)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        column.pack_start(render, True)
        column.set_cell_data_func(render, cdf)

        render = Gtk.CellRendererText()
        render.props.sensitive = False
        column.pack_start(render, False)
        column.set_cell_data_func(render, cdf_count)

        view.append_column(column)

        unhide = qltk.Button(_("Unhide"), Gtk.STOCK_ADD)
        unhide.connect_object("clicked", self.__unhide, view, library)
        remove = Gtk.Button(stock=Gtk.STOCK_REMOVE)

        selection = view.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        selection.connect("changed", self.__select_changed, remove, unhide)
        selection.emit("changed")

        remove.connect_object("clicked", self.__remove, view, library)

        vbox = Gtk.VBox(spacing=6)
        vbox.pack_start(unhide, False, True, 0)
        vbox.pack_start(remove, False, True, 0)

        self.pack_start(sw, True, True, 0)
        self.pack_start(vbox, False, True, 0)

        for path in library.masked_mount_points:
            model.append(row=[path])

        if not len(model):
            self.set_sensitive(False)

        for child in self.get_children():
            child.show_all()

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __unhide(self, view, library):
        selection = view.get_selection()
        model, paths = selection.get_selected_rows()
        for path in paths:
            library.unmask(model[path][0])
        view.remove_selection()

    def __select_changed(self, selection, *buttons):
        active = bool(selection.count_selected_rows())
        for button in buttons:
            button.set_sensitive(active)

    def __remove(self, view, library):
        dialog = ConfirmMaskedRemoval(self)
        response = dialog.run()
        if response == Gtk.ResponseType.YES:
            selection = view.get_selection()
            model, paths = selection.get_selected_rows()
            for path in paths:
                library.remove_masked(model[path][0])
            view.remove_selection()
