# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import sre
import gtk, pango, gobject

import stock
import qltk
from qltk.wlw import WritingWindow
from qltk.views import HintedTreeView
from qltk.cbes import ComboBoxEntrySave
from qltk.ccb import ConfigCheckButton
import const
import config
import util
import unicodedata

from library import library
from parse import FileFromPattern

class FilterCheckButton(ConfigCheckButton):
    def __init__(self):
        super(FilterCheckButton, self).__init__(
            self._label, "rename", self._key)
        try: self.set_active(config.getboolean("rename", self._key))
        except: pass
    active = property(lambda s: s.get_active())

    def filter(self, filename): raise NotImplementedError

class SpacesToUnderscores(FilterCheckButton):
    _label = _("Replace spaces with underscores")
    _key = "spaces"
    def filter(self, filename): return filename.replace(" ", "_")

class StripWindowsIncompat(FilterCheckButton):
    _label = _("Strip _Windows-incompatible characters")
    _key = "windows"
    BAD = '\:*?;"<>|'
    def filter(self, filename):
        return "".join(map(lambda s: (s in self.BAD and "_") or s, filename))

class StripDiacriticals(FilterCheckButton):
    _label = _("Strip _diacritical marks")
    _key = "diacriticals"
    def filter(self, filename):
        return filter(lambda s: not unicodedata.combining(s),
                      unicodedata.normalize('NFKD', filename))

class StripNonASCII(FilterCheckButton):
    _label = _("Strip non-_ASCII characters")
    _key = "ascii"
    def filter(self, filename):
        return "".join(map(lambda s: (s <= "~" and s) or "_", filename))

class RenameFiles(gtk.VBox):
    FILTERS = [SpacesToUnderscores, StripWindowsIncompat, StripDiacriticals,
               StripNonASCII]

    def __init__(self, prop, watcher):
        gtk.VBox.__init__(self, spacing=6)
        self.title = _("Rename Files")
        self.set_border_width(12)

        # ComboEntry and Preview button
        hbox = gtk.HBox(spacing=12)
        combo = ComboBoxEntrySave(
            const.NBP, const.NBP_EXAMPLES.split("\n"))
        hbox.pack_start(combo)
        preview = gtk.Button(stock=stock.PREVIEW)
        hbox.pack_start(preview, expand=False)
        self.pack_start(hbox, expand=False)

        # Tree view in a scrolling window
        model = gtk.ListStore(object, str, str)
        view = gtk.TreeView(model)
        column = gtk.TreeViewColumn(
            _('File'), gtk.CellRendererText(), text=1)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(column)
        render = gtk.CellRendererText()
        render.set_property('editable', True)

        column = gtk.TreeViewColumn(_('New Name'), render, text=2)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        view.append_column(column)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(view)
        self.pack_start(sw)

        hb = gtk.HBox()
        expander = gtk.Expander(label=_("_More options..."))
        expander.set_use_underline(True)
        adj = gtk.Alignment(yalign=1.0, xscale=1.0)
        adj.add(expander)
        hb.pack_start(adj)

        # Save button
        save = gtk.Button(stock=gtk.STOCK_SAVE)
        bbox = gtk.HButtonBox()
        bbox.set_layout(gtk.BUTTONBOX_END)
        bbox.pack_start(save)
        hb.pack_start(bbox, expand=False)
        self.pack_start(hb, expand=False)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        vbox = gtk.VBox()
        self.__filters = [Kind() for Kind in self.FILTERS]
        map(vbox.pack_start, self.__filters)
        sw.add_with_viewport(vbox)
        self.pack_start(sw, expand=False)

        expander.connect("notify::expanded", self.__notify_expanded, sw)
        expander.set_expanded(False)

        # Connect callbacks
        preview_args = [combo, prop, model, save, preview]
        preview.connect('clicked', self.__preview_files, *preview_args)
        prop.connect_object(
            'changed', self.__class__.__update, self, *preview_args)

        for w in self.__filters:
            w.connect('toggled', self.__preview_files, *preview_args)
        changed_args = [save, preview, combo.child]
        combo.child.connect_object('changed', self.__changed, *changed_args)

        save.connect_object(
            'clicked', self.__rename_files, prop, save, model, watcher)

        render.connect('edited', self.__row_edited, model, preview, save)
        self.show_all()
        sw.hide()

    def __notify_expanded(self, expander, event, vbox):
        vbox.set_property('visible', expander.get_property('expanded'))

    def __changed(self, save, preview, entry):
        save.set_sensitive(False)
        preview.set_sensitive(bool(entry.get_text()))

    def __row_edited(self, renderer, path, new, model, preview, save):
        row = model[path]
        if row[2] != new:
            row[2] = new
            preview.set_sensitive(True)
            save.set_sensitive(True)

    def __preview_files(self, button, *args):
        self.__update(self.__songs, *args)
        save = args[3]
        save.set_sensitive(True)
        preview = args[4]
        preview.set_sensitive(False)

    def __rename_files(self, parent, save, model, watcher):
        win = WritingWindow(parent, len(self.__songs))
        was_changed = []
        skip_all = False

        for row in model:
            song = row[0]
            oldname = row[1]
            newname = row[2].decode('utf-8')
            try:
                newname = newname.encode(util.fscoding, "replace")
                if library: library.rename(song, newname)
                else: song.rename(newname)
                was_changed.append(song)
            except:
                if skip_all: continue
                buttons = (gtk.STOCK_STOP, gtk.RESPONSE_CANCEL,
                           _("_Continue"), gtk.RESPONSE_OK)
                msg = qltk.Message(
                    gtk.MESSAGE_ERROR, win, _("Unable to rename file"),
                    _("Renaming <b>%s</b> to <b>%s</b> failed. "
                      "Possibly the target file already exists, "
                      "or you do not have permission to make the "
                      "new file or remove the old one.") %(
                    util.escape(util.fsdecode(oldname)),
                    util.escape(util.fsdecode(newname))),
                    buttons=gtk.BUTTONS_NONE)
                msg.add_buttons(*buttons)
                msg.set_default_response(gtk.RESPONSE_OK)
                resp = msg.run()
                mods = gtk.gdk.display_get_default().get_pointer()[3]
                skip_all |= mods & gtk.gdk.SHIFT_MASK
                watcher.reload(song)
                if resp != gtk.RESPONSE_OK: break
            if win.step(): break

        win.destroy()
        watcher.changed(was_changed)
        watcher.refresh()
        save.set_sensitive(False)

    def __update(self, songs, combo, parent, model, save, preview):
        self.__songs = songs
        model.clear()
        pattern = combo.child.get_text().decode("utf-8")

        try:
            pattern = FileFromPattern(pattern)
        except ValueError: 
            qltk.ErrorMessage(
                parent,
                _("Path is not absolute"),
                _("The pattern\n\t<b>%s</b>\ncontains / but "
                  "does not start from root. To avoid misnamed "
                  "folders, root your pattern by starting "
                  "it with / or ~/.")%(
                util.escape(pattern))).run()
            return
        else:
            if combo.child.get_text():
                combo.prepend_text(combo.child.get_text())
                combo.write(const.NBP)

        for song in self.__songs:
            newname = pattern.format(song)
            code = util.fscoding
            newname = newname.encode(code, "replace").decode(code)
            for f in self.__filters:
                if f.active: newname = f.filter(newname)
            basename = song("~basename").decode(code, "replace")
            model.append(row=[song, basename, newname])
        preview.set_sensitive(False)
        save.set_sensitive(bool(combo.child.get_text()))
        for song in songs:
            if not song.is_file:
                self.set_sensitive(False)
                break
        else: self.set_sensitive(True)
