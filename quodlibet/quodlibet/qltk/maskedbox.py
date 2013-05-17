# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import pango

from quodlibet import util
from quodlibet import qltk
from quodlibet.qltk.views import RCMHintedTreeView


class ConfirmMaskedRemoval(qltk.Message):
    def __init__(self, parent):
        title = _("Are you sure you want to remove all songs?")
        description = _("The selected songs will be removed from the library.")

        super(ConfirmMaskedRemoval, self).__init__(
            gtk.MESSAGE_WARNING, parent, title, description, gtk.BUTTONS_NONE)

        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_REMOVE, gtk.RESPONSE_YES)


class MaskedBox(gtk.HBox):

    def __init__(self, library):
        super(MaskedBox, self).__init__(spacing=6)

        self.model = model = gtk.ListStore(object)
        view = RCMHintedTreeView(model)
        view.set_fixed_height_mode(True)
        view.set_headers_visible(False)
        self.view = view

        menu = gtk.Menu()
        unhide_item = qltk.MenuItem(_("Unhide"), gtk.STOCK_ADD)
        unhide_item.connect_object('activate', self.__unhide, view, library)
        menu.append(unhide_item)

        remove_item = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        remove_item.connect_object('activate', self.__remove, view, library)
        menu.append(remove_item)

        menu.show_all()
        view.connect('popup-menu', self.__popup, menu)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        sw.set_size_request(-1, max(sw.size_request()[1], 80))

        def cdf(column, cell, model, iter):
            row = model[iter]
            cell.set_property('text', util.fsdecode(row[0]))

        def cdf_count(column, cell, model, iter):
            mount = model[iter][0]
            song_count = len(library.get_masked(mount))
            cell.set_property('text',
                _("%(song_count)d songs") % {"song_count": song_count})

        column = gtk.TreeViewColumn(None)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(render)
        column.set_cell_data_func(render, cdf)

        render = gtk.CellRendererText()
        render.props.sensitive = False
        column.pack_start(render, expand=False)
        column.set_cell_data_func(render, cdf_count)

        view.append_column(column)

        unhide = qltk.Button(_("Unhide"), gtk.STOCK_ADD)
        unhide.connect_object("clicked", self.__unhide, view, library)
        remove = gtk.Button(stock=gtk.STOCK_REMOVE)

        selection = view.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect("changed", self.__select_changed, remove, unhide)
        selection.emit("changed")

        remove.connect_object("clicked", self.__remove, view, library)

        vbox = gtk.VBox(spacing=6)
        vbox.pack_start(unhide, expand=False)
        vbox.pack_start(remove, expand=False)

        self.pack_start(sw)
        self.pack_start(vbox, expand=False)
        self.show_all()

        for path in library.masked_mount_points:
            model.append(row=[path])

        if not len(model):
            self.set_sensitive(False)

    def __popup(self, view, menu):
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

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
        if response == gtk.RESPONSE_YES:
            selection = view.get_selection()
            model, paths = selection.get_selected_rows()
            for path in paths:
                library.remove_masked(model[path][0])
            view.remove_selection()
