# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk
from senf import fsn2text

from quodlibet import qltk
from quodlibet import util
from quodlibet import _
from quodlibet.formats import AudioFileError
from quodlibet.qltk._editutils import OverwriteWarning, WriteFailedError
from quodlibet.qltk.views import HintedTreeView, TreeViewColumn
from quodlibet.qltk.wlw import WritingWindow
from quodlibet.qltk.x import Button, Align
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk import Icons
from quodlibet.util import connect_obj, gdecode
from quodlibet.compat import text_type, itervalues


class Entry(object):

    def __init__(self, song):
        self.song = song
        self.tracknumber = song("tracknumber")

    @property
    def name(self):
        return fsn2text(self.song("~basename"))


class TrackNumbers(Gtk.VBox):
    def __init__(self, prop, library):
        super(TrackNumbers, self).__init__(spacing=6)
        self.title = _("Track Numbers")
        self.set_border_width(12)

        label_start = Gtk.Label(label=_("Start fro_m:"), halign=Gtk.Align.END)
        label_start.set_use_underline(True)
        spin_start = Gtk.SpinButton()
        spin_start.set_range(0, 999)
        spin_start.set_increments(1, 10)
        spin_start.set_value(1)
        label_start.set_mnemonic_widget(spin_start)

        label_total = Gtk.Label(
            label=_("_Total tracks:"), halign=Gtk.Align.END)
        label_total.set_use_underline(True)
        spin_total = Gtk.SpinButton()
        spin_total.set_range(0, 999)
        spin_total.set_increments(1, 10)
        label_total.set_mnemonic_widget(spin_total)

        preview = qltk.Button(_("_Preview"), Icons.VIEW_REFRESH)

        grid = Gtk.Grid(row_spacing=4, column_spacing=4)
        grid.add(label_start)
        grid.attach_next_to(
            spin_start, label_start, Gtk.PositionType.RIGHT, 1, 1)
        grid.attach_next_to(
            label_total, label_start, Gtk.PositionType.BOTTOM, 1, 1)
        grid.attach_next_to(
            spin_total, label_total, Gtk.PositionType.RIGHT, 1, 1)
        grid.attach_next_to(
            Align(preview, halign=Gtk.Align.END),
            spin_start, Gtk.PositionType.RIGHT, 1, 1)
        preview.props.hexpand = True

        model = ObjectStore()
        view = HintedTreeView(model=model)

        self.pack_start(grid, False, True, 0)

        render = Gtk.CellRendererText()
        column = TreeViewColumn(title=_('File'))
        column.pack_start(render, True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

        def cell_data_file(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property("text", entry.name)

        column.set_cell_data_func(render, cell_data_file)

        view.append_column(column)
        render = Gtk.CellRendererText()
        render.set_property('editable', True)
        column = TreeViewColumn(title=_('Track'))
        column.pack_start(render, True)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)

        def cell_data_track(column, cell, model, iter_, data):
            entry = model.get_value(iter_)
            cell.set_property("text", entry.tracknumber)

        column.set_cell_data_func(render, cell_data_track)

        view.append_column(column)
        view.set_reorderable(True)
        w = Gtk.ScrolledWindow()
        w.set_shadow_type(Gtk.ShadowType.IN)
        w.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        w.add(view)
        self.pack_start(w, True, True, 0)

        bbox = Gtk.HButtonBox()
        bbox.set_spacing(6)
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        save = Button(_("_Save"), Icons.DOCUMENT_SAVE)
        self.save = save
        connect_obj(save,
            'clicked', self.__save_files, prop, model, library)
        revert = Button(_("_Revert"), Icons.DOCUMENT_REVERT)
        self.revert = revert
        bbox.pack_start(revert, True, True, 0)
        bbox.pack_start(save, True, True, 0)
        self.pack_start(bbox, False, True, 0)

        preview_args = [spin_start, spin_total, model, save, revert]
        preview.connect('clicked', self.__preview_tracks, *preview_args)
        connect_obj(revert, 'clicked',
                              self.__update, None, *preview_args[1:])
        spin_total.connect(
            'value-changed', self.__preview_tracks, *preview_args)
        spin_start.connect(
            'value-changed', self.__preview_tracks, *preview_args)
        connect_obj(view,
            'drag-end', self.__class__.__preview_tracks, self,
            *preview_args)
        render.connect('edited', self.__row_edited, model, preview, save)

        connect_obj(prop,
            'changed', self.__class__.__update, self,
            spin_total, model, save, revert)

        for child in self.get_children():
            child.show_all()

    def __row_edited(self, render, path, new, model, preview, save):
        path = Gtk.TreePath.new_from_string(path)
        row = model[path]
        entry = row[0]
        new = gdecode(new)
        if entry.tracknumber != new:
            entry.tracknumber = new
            preview.set_sensitive(True)
            save.set_sensitive(True)
            model.path_changed(path)

    def __save_files(self, parent, model, library):
        win = WritingWindow(parent, len(model))
        was_changed = set()
        all_done = False
        for entry in itervalues(model):
            song, track = entry.song, entry.tracknumber
            if song.get("tracknumber") == track:
                win.step()
                continue
            if not song.valid():
                win.hide()
                dialog = OverwriteWarning(self, song)
                resp = dialog.run()
                win.show()
                if resp != OverwriteWarning.RESPONSE_SAVE:
                    break
            song["tracknumber"] = track
            try:
                song.write()
            except AudioFileError:
                util.print_exc()
                WriteFailedError(self, song).run()
                library.reload(song, changed=was_changed)
                break
            was_changed.add(song)
            if win.step():
                break
        else:
            all_done = True

        library.changed(was_changed)
        win.destroy()
        self.save.set_sensitive(not all_done)
        self.revert.set_sensitive(not all_done)

    def __preview_tracks(self, ctx, start, total, model, save, revert):
        start = start.get_value_as_int()
        total = total.get_value_as_int()
        for row in model:
            if total:
                s = u"%d/%d" % (row.path.get_indices()[0] + start, total)
            else:
                s = text_type(row.path.get_indices()[0] + start)
            entry = row[0]
            entry.tracknumber = s
            model.row_changed(row.path, row.iter)

        save.set_sensitive(True)
        revert.set_sensitive(True)

    def __update(self, songs, total, model, save, revert):
        if songs is None:
            songs = [e.song for e in itervalues(model)]
        else:
            songs = list(songs)

        def sort_key(song):
            return song("~#track", 0), song("~basename"), song
        songs.sort(key=sort_key)

        model.clear()
        total.set_value(len(songs))

        for song in songs:
            if not song.can_change("tracknumber"):
                self.set_sensitive(False)
                break
        else:
            self.set_sensitive(True)

        for song in songs:
            model.append([Entry(song)])

        save.set_sensitive(False)
        revert.set_sensitive(False)
