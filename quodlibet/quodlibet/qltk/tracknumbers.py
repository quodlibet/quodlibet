# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import qltk
from quodlibet import util

from quodlibet.qltk.views import HintedTreeView, TreeViewColumn
from quodlibet.qltk.wlw import WritingWindow


class TrackNumbers(Gtk.VBox):
    def __init__(self, prop, library):
        super(TrackNumbers, self).__init__(spacing=6)
        self.title = _("Track Numbers")
        self.set_border_width(12)
        hbox2 = Gtk.HBox(spacing=12)

        hbox_start = Gtk.HBox(spacing=3)
        label_start = Gtk.Label(label=_("Start fro_m:"))
        label_start.set_use_underline(True)
        spin_start = Gtk.SpinButton()
        spin_start.set_range(0, 999)
        spin_start.set_increments(1, 10)
        spin_start.set_value(1)
        label_start.set_mnemonic_widget(spin_start)
        hbox_start.pack_start(label_start, True, True, 0)
        hbox_start.pack_start(spin_start, True, True, 0)

        hbox_total = Gtk.HBox(spacing=3)
        label_total = Gtk.Label(label=_("_Total tracks:"))
        label_total.set_use_underline(True)
        spin_total = Gtk.SpinButton()
        spin_total.set_range(0, 999)
        spin_total.set_increments(1, 10)
        label_total.set_mnemonic_widget(spin_total)
        hbox_total.pack_start(label_total, True, True, 0)
        hbox_total.pack_start(spin_total, True, True, 0)
        preview = qltk.Button(_("_Preview"), Gtk.STOCK_CONVERT)

        hbox2.pack_start(hbox_start, True, False, 0)
        hbox2.pack_start(hbox_total, True, False, 0)
        hbox2.pack_start(preview, False, True, 0)

        model = Gtk.ListStore(object, str, str)
        view = HintedTreeView(model)

        self.pack_start(hbox2, False, True, 0)

        render = Gtk.CellRendererText()
        column = TreeViewColumn(_('File'), render, text=1)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        view.append_column(column)
        render = Gtk.CellRendererText()
        render.set_property('editable', True)
        column = TreeViewColumn(_('Track'), render, text=2)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        view.append_column(column)
        view.set_reorderable(True)
        w = Gtk.ScrolledWindow()
        w.set_shadow_type(Gtk.ShadowType.IN)
        w.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        w.add(view)
        self.pack_start(w, True, True, 0)

        bbox = Gtk.HButtonBox()
        bbox.set_spacing(12)
        bbox.set_layout(Gtk.ButtonBoxStyle.END)
        save = Gtk.Button(stock=Gtk.STOCK_SAVE)
        save.connect_object(
            'clicked', self.__save_files, prop, model, library)
        revert = Gtk.Button(stock=Gtk.STOCK_REVERT_TO_SAVED)
        bbox.pack_start(revert, True, True, 0)
        bbox.pack_start(save, True, True, 0)
        self.pack_start(bbox, False, True, 0)

        preview_args = [spin_start, spin_total, model, save, revert]
        preview.connect('clicked', self.__preview_tracks, *preview_args)
        revert.connect_object('clicked', self.__update, None, *preview_args[1:])
        spin_total.connect(
            'value-changed', self.__preview_tracks, *preview_args)
        spin_start.connect(
            'value-changed', self.__preview_tracks, *preview_args)
        view.connect_object(
            'drag-end', self.__class__.__preview_tracks, self,
            *preview_args)
        render.connect('edited', self.__row_edited, model, preview, save)

        prop.connect_object(
            'changed', self.__class__.__update, self,
            spin_total, model, save, revert)

        self.show_all()

    def __row_edited(self, render, path, new, model, preview, save):
        row = model[path]
        if row[2] != new:
            row[2] = new
            preview.set_sensitive(True)
            save.set_sensitive(True)

    def __save_files(self, parent, model, library):
        win = WritingWindow(parent, len(model))
        was_changed = []
        for row in model:
            song = row[0]
            track = row[2]
            if song.get("tracknumber") == track:
                win.step()
                continue
            if not song.valid() and not qltk.ConfirmAction(
                win, _("Tag may not be accurate"),
                _("<b>%s</b> changed while the program was running. "
                  "Saving without refreshing your library may "
                  "overwrite other changes to the song.\n\n"
                  "Save this song anyway?") %(
                util.escape(util.fsdecode(song("~basename"))))
                ).run():
                break
            song["tracknumber"] = track
            try: song.write()
            except:
                util.print_exc()
                qltk.ErrorMessage(
                    win, _("Unable to save song"),
                    _("Saving <b>%s</b> failed. The file may be "
                      "read-only, corrupted, or you do not have "
                      "permission to edit it.")%(
                    util.escape(util.fsdecode(song('~basename'))))).run()
                library.reload(song, changed=was_changed)
                break
            was_changed.append(song)
            if win.step(): break
        library.changed(was_changed)
        win.destroy()

    def __preview_tracks(self, ctx, start, total, model, save, revert):
        start = start.get_value_as_int()
        total = total.get_value_as_int()
        for row in model:
            if total: s = "%d/%d" % (row.path[0] + start, total)
            else: s = str(row.path[0] + start)
            row[2] = s
        save.set_sensitive(True)
        revert.set_sensitive(True)

    def __update(self, songs, total, model, save, revert):
        if songs is None:
            songs = [row[0] for row in model]
        else:
            songs = list(songs)
        songs.sort(
            key=lambda song: (song("~#track"), song("~basename"), song))
        model.clear()
        total.set_value(len(songs))
        for song in songs:
            if not song.can_change("tracknumber"):
                self.set_sensitive(False)
                break
        else: self.set_sensitive(True)
        for song in songs:
            basename = util.fsdecode(song("~basename"))
            model.append(row=[song, basename, song("tracknumber")])
        save.set_sensitive(False)
        revert.set_sensitive(False)
