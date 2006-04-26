# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk

import qltk
import stock
import util

from qltk.wlw import WritingWindow
from qltk.views import HintedTreeView

class TrackNumbers(gtk.VBox):
    def __init__(self, prop, watcher):
        gtk.VBox.__init__(self, spacing=6)
        self.title = _("Track Numbers")
        self.set_border_width(12)
        hbox = gtk.HBox(spacing=18)
        hbox2 = gtk.HBox(spacing=12)

        hbox_start = gtk.HBox(spacing=3)
        label_start = gtk.Label(_("Start fro_m:"))
        label_start.set_use_underline(True)
        spin_start = gtk.SpinButton()
        spin_start.set_range(0, 99)
        spin_start.set_increments(1, 10)
        spin_start.set_value(1)
        label_start.set_mnemonic_widget(spin_start)
        hbox_start.pack_start(label_start)
        hbox_start.pack_start(spin_start)

        hbox_total = gtk.HBox(spacing=3)
        label_total = gtk.Label(_("_Total tracks:"))
        label_total.set_use_underline(True)
        spin_total = gtk.SpinButton()
        spin_total.set_range(0, 99)
        spin_total.set_increments(1, 10)
        label_total.set_mnemonic_widget(spin_total)
        hbox_total.pack_start(label_total)
        hbox_total.pack_start(spin_total)
        preview = gtk.Button(stock=stock.PREVIEW)

        hbox2.pack_start(hbox_start, expand=True, fill=False)
        hbox2.pack_start(hbox_total, expand=True, fill=False)
        hbox2.pack_start(preview, expand=False, fill=True)

        model = gtk.ListStore(object, str, str)
        view = HintedTreeView(model)

        self.pack_start(hbox2, expand=False)

        render = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_('File'), render, text=1)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(column)
        render = gtk.CellRendererText()
        render.set_property('editable', True)
        column = gtk.TreeViewColumn(_('Track'), render, text=2)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(column)
        view.set_reorderable(True)
        w = gtk.ScrolledWindow()
        w.set_shadow_type(gtk.SHADOW_IN)
        w.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        w.add(view)
        self.pack_start(w)

        bbox = gtk.HButtonBox()
        bbox.set_spacing(12)
        bbox.set_layout(gtk.BUTTONBOX_END)
        save = gtk.Button(stock=gtk.STOCK_SAVE)
        save.connect_object(
            'clicked', self.__save_files, prop, model, watcher)
        revert = gtk.Button(stock=gtk.STOCK_REVERT_TO_SAVED)
        revert.connect_object(
            'clicked', self.__revert_files, spin_total, model,
            save, revert)
        bbox.pack_start(revert)
        bbox.pack_start(save)
        self.pack_start(bbox, expand=False)

        preview_args = [spin_start, spin_total, model, save, revert]
        preview.connect('clicked', self.__preview_tracks, *preview_args)
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

    def __save_files(self, parent, model, watcher):
        win = WritingWindow(parent, len(self.__songs))
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
                qltk.ErrorMessage(
                    win, _("Unable to save song"),
                    _("Saving <b>%s</b> failed. The file may be "
                      "read-only, corrupted, or you do not have "
                      "permission to edit it.")%(
                    util.escape(util.fsdecode(song('~basename'))))).run()
                watcher.reload(song)
                break
            was_changed.append(song)
            if win.step(): break
        watcher.changed(was_changed)
        win.destroy()

    def __revert_files(self, *args):
        self.__update(self.__songs, *args)

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
        songs = songs[:]
        songs.sort(lambda a, b: (cmp(a("~#track"), b("~#track")) or
                                 cmp(a("~basename"), b("~basename")) or
                                 cmp(a, b)))
        self.__songs = songs
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
