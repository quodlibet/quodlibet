# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#                2012 Nick Boultbee
#                2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, GObject, Pango
from senf import fsn2text

from quodlibet import ngettext, _
from quodlibet import qltk
from quodlibet import config

from quodlibet.qltk.edittags import EditTags
from quodlibet.qltk.renamefiles import RenameFiles
from quodlibet.qltk.tagsfrompath import TagsFromPath
from quodlibet.qltk.tracknumbers import TrackNumbers
from quodlibet.qltk.views import HintedTreeView
from quodlibet.qltk.window import PersistentWindowMixin
from quodlibet.qltk.x import ScrolledWindow, ConfigRPaned
from quodlibet.qltk.models import ObjectStore, ObjectModelSort
from quodlibet.qltk.msg import CancelRevertSave
from quodlibet.util import connect_destroy
from quodlibet.compat import cmp


class _ListEntry(object):

    def __init__(self, song):
        self.song = song

    @property
    def name(self):
        return fsn2text(self.song("~basename"))


class SongProperties(qltk.Window, PersistentWindowMixin):
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, (object,))
    }

    def __init__(self, library, songs, parent=None):
        super(SongProperties, self).__init__(dialog=False)
        self.set_transient_for(qltk.get_top_parent(parent))

        default_width = 600
        config_suffix = ""
        if len(songs) <= 1:
            default_width -= 200
            config_suffix += "single"
        self.set_default_size(default_width, 400)

        self.enable_window_tracking("quodlibet_properties",
                                    size_suffix=config_suffix)

        self.auto_save_on_change = config.getboolean(
                'editing', 'auto_save_changes', False)

        paned = ConfigRPaned("memory", "quodlibet_properties_pos", 0.4)
        notebook = qltk.Notebook()
        notebook.props.scrollable = True
        pages = []
        pages.extend([Ctr(self, library) for Ctr in
                      [EditTags, TagsFromPath, RenameFiles]])
        if len(songs) > 1:
            pages.append(TrackNumbers(self, library))
        for page in pages:
            page.show()
            notebook.append_page(page)

        fbasemodel = ObjectStore()
        fmodel = ObjectModelSort(model=fbasemodel)
        fview = HintedTreeView(model=fmodel)
        fview.connect('button-press-event', self.__pre_selection_changed)
        fview.set_rules_hint(True)
        selection = fview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.__save = None

        render = Gtk.CellRendererText()
        c1 = Gtk.TreeViewColumn(_('File'), render)
        if fview.supports_hints():
            render.set_property('ellipsize', Pango.EllipsizeMode.END)
        render.set_property('xpad', 3)

        def cell_data(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property('text', entry.name)

        c1.set_cell_data_func(render, cell_data)

        def sort_func(model, a, b, data):
            a = model.get_value(a)
            b = model.get_value(b)
            return cmp(a.name, b.name)

        fmodel.set_sort_func(100, sort_func)
        c1.set_sort_column_id(100)
        fview.append_column(c1)

        sw = ScrolledWindow()
        sw.add(fview)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        # only show the list if there are is more than one song
        if len(songs) > 1:
            sw.show_all()

        paned.pack1(sw, shrink=False, resize=True)

        for song in songs:
            fbasemodel.append(row=[_ListEntry(song)])

        self.connect("changed", self.__on_changed)

        selection.select_all()
        paned.pack2(notebook, shrink=False, resize=True)

        csig = selection.connect('changed', self.__selection_changed)
        connect_destroy(library,
            'changed', self.__on_library_changed, fbasemodel, fview)
        connect_destroy(library,
            'removed', self.__on_library_removed, fbasemodel, selection, csig)

        self.emit('changed', songs)
        self.add(paned)
        paned.set_position(175)
        notebook.show()
        paned.show()

    def __on_library_removed(self, library, songs, model, selection, sig):
        selection.handler_block(sig)

        rows = selection.get_selected_rows()[1]
        to_remove = []
        changed = False
        for row in model:
            if row[0].song in songs:
                to_remove.append(row.iter)
                changed = changed or (row.path in rows)
        for iter_ in to_remove:
            model.remove(iter_)

        selection.handler_unblock(sig)
        if changed:
            selection.emit('changed')

    def __on_changed(self, widget, songs):
        if songs:
            if len(songs) == 1:
                title = songs[0].comma("title")
            else:
                title = ngettext(
                    "%(title)s and %(count)d more",
                    "%(title)s and %(count)d more",
                    len(songs) - 1) % {'title': songs[0].comma("title"),
                                       'count': len(songs) - 1}
            self.set_title("%s - %s" % (title, _("Properties")))
        else:
            self.set_title(_("Properties"))

        self.set_pending(None)

    def __on_library_changed(self, library, songs, model, view):
        # in case the library changes, sync the model and emit
        # selection changed if one of the selected was changed

        paths = view.get_selection().get_selected_rows()[1]

        changed = False
        for row in model:
            song = row[0].song
            if song in songs:
                model.row_changed(row.path, row.iter)
                changed = changed or (row.path in paths)

        if changed:
            view.get_selection().emit('changed')

    def set_pending(self, button, *excess):
        self.__save = button

    def __pre_selection_changed(self, view, event):
        if self.__save:
            if self.auto_save_on_change:
                self.__save.clicked()
                return
            resp = CancelRevertSave(self).run()
            if resp == Gtk.ResponseType.YES:
                self.__save.clicked()
            elif resp == Gtk.ResponseType.NO:
                return False
            else:
                return True # cancel or closed

    def __selection_changed(self, selection):
        model = selection.get_tree_view().get_model()
        model, paths = selection.get_selected_rows()
        songs = [model[path][0].song for path in paths]
        self.emit('changed', songs)
