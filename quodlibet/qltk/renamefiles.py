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
from qltk.cbes import ComboBoxEntrySave
from qltk.ccb import ConfigCheckButton
from qltk._editpane import EditPane
import const
import config
import util
import unicodedata

from library import library
from parse import FileFromPattern

class FilterCheckButton(ConfigCheckButton):
    __gsignals__ = {
        "preview": (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
        }

    def __init__(self):
        super(FilterCheckButton, self).__init__(
            self._label, "rename", self._key)
        try: self.set_active(config.getboolean("rename", self._key))
        except: pass
        self.connect_object('toggled', self.emit, 'preview')
    active = property(lambda s: s.get_active())

    def filter(self, original, filename): raise NotImplementedError

    def __cmp__(self, other):
        return (cmp(self._order, other._order) or
                cmp(type(self).__name__, type(other).__name__))
gobject.type_register(FilterCheckButton)

class SpacesToUnderscores(FilterCheckButton):
    _label = _("Replace spaces with _underscores")
    _key = "spaces"
    _order = 1.0
    def filter(self, original, filename): return filename.replace(" ", "_")

class StripWindowsIncompat(FilterCheckButton):
    _label = _("Strip _Windows-incompatible characters")
    _key = "windows"
    BAD = '\:*?;"<>|'
    _order = 1.1
    def filter(self, original, filename):
        return "".join(map(lambda s: (s in self.BAD and "_") or s, filename))

class StripDiacriticals(FilterCheckButton):
    _label = _("Strip _diacritical marks")
    _key = "diacriticals"
    _order = 1.2
    def filter(self, original, filename):
        return filter(lambda s: not unicodedata.combining(s),
                      unicodedata.normalize('NFKD', filename))

class StripNonASCII(FilterCheckButton):
    _label = _("Strip non-_ASCII characters")
    _key = "ascii"
    _order = 1.3
    def filter(self, original, filename):
        return "".join(map(lambda s: (s <= "~" and s) or "_", filename))

class RenameFiles(EditPane):
    title = _("Rename Files")
    FILTERS = [SpacesToUnderscores, StripWindowsIncompat, StripDiacriticals,
               StripNonASCII]

    def __init__(self, parent, watcher):
        plugins = parent.plugins.RenamePlugins()
        super(RenameFiles, self).__init__(
            const.NBP, const.NBP_EXAMPLES.split("\n"), plugins)

        column = gtk.TreeViewColumn(
            _('File'), gtk.CellRendererText(), text=1)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.view.append_column(column)
        render = gtk.CellRendererText()
        render.set_property('editable', True)

        column = gtk.TreeViewColumn(_('New Name'), render, text=2)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.view.append_column(column)

        self.preview.connect_object('clicked', self.__preview, None)

        parent.connect_object('changed', self.__class__.__preview, self)
        self.save.connect_object('clicked', self.__rename, watcher)

        render.connect('edited', self.__row_edited)

    def __row_edited(self, renderer, path, new):
        row = self.view.get_model()[path]
        if row[2] != new:
            row[2] = new
            self.preview.set_sensitive(True)
            self.save.set_sensitive(True)

    def __rename(self, watcher):
        win = WritingWindow(self, len(self.__songs))
        was_changed = []
        skip_all = False

        for row in self.view.get_model():
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
        self.save.set_sensitive(False)

    def __preview(self, songs):
        if songs is None: songs = self.__songs
        else: self.__songs = songs
        model = self.view.get_model()
        model.clear()
        pattern = self.combo.child.get_text().decode("utf-8")

        try:
            pattern = FileFromPattern(pattern)
        except ValueError: 
            qltk.ErrorMessage(
                self, _("Path is not absolute"),
                _("The pattern\n\t<b>%s</b>\ncontains / but "
                  "does not start from root. To avoid misnamed "
                  "folders, root your pattern by starting "
                  "it with / or ~/.")%(
                util.escape(pattern))).run()
            return
        else:
            if self.combo.child.get_text():
                self.combo.prepend_text(self.combo.child.get_text())
                self.combo.write(const.NBP)

        for song in self.__songs:
            newname = pattern.format(song)
            code = util.fscoding
            newname = newname.encode(code, "replace").decode(code)
            for f in self.filters:
                if f.active: newname = f.filter(song["~filename"], newname)
            basename = song("~basename").decode(code, "replace")
            model.append(row=[song, basename, newname])
        self.preview.set_sensitive(False)
        self.save.set_sensitive(bool(self.combo.child.get_text()))
        for song in songs:
            if not song.is_file:
                self.set_sensitive(False)
                break
        else: self.set_sensitive(True)
