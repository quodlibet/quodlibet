# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import unicodedata

import gtk

from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.parse import FileFromPattern
from quodlibet.qltk._editpane import EditPane, FilterCheckButton
from quodlibet.qltk._editpane import EditingPluginHandler
from quodlibet.qltk.views import TreeViewColumn
from quodlibet.qltk.wlw import WritingWindow

class SpacesToUnderscores(FilterCheckButton):
    _label = _("Replace spaces with _underscores")
    _section = "rename"
    _key = "spaces"
    _order = 1.0
    def filter(self, original, filename): return filename.replace(" ", "_")

class StripWindowsIncompat(FilterCheckButton):
    _label = _("Strip _Windows-incompatible characters")
    _section = "rename"
    _key = "windows"
    _order = 1.1
    def __init__(self):
        super(StripWindowsIncompat, self).__init__()
        # If on Windows, force this to be inactive (and hidden)
        if os.name == 'nt':
            self.set_active(False)
            self.set_sensitive(False)
            self.set_no_show_all(True)
    def filter(self, original, filename):
        return util.strip_win32_incompat(filename)

class StripDiacriticals(FilterCheckButton):
    _label = _("Strip _diacritical marks")
    _section = "rename"
    _key = "diacriticals"
    _order = 1.2
    def filter(self, original, filename):
        return filter(lambda s: not unicodedata.combining(s),
                      unicodedata.normalize('NFKD', filename))

class StripNonASCII(FilterCheckButton):
    _label = _("Strip non-_ASCII characters")
    _section = "rename"
    _key = "ascii"
    _order = 1.3
    def filter(self, original, filename):
        return u"".join(map(lambda s: (s <= "~" and s) or u"_", filename))

class Lowercase(FilterCheckButton):
    _label = _("Use only _lowercase characters")
    _section = "rename"
    _key = "lowercase"
    _order = 1.4
    def filter(self, original, filename):
        return filename.lower()


class RenameFilesPluginHandler(EditingPluginHandler):
    from quodlibet.plugins.editing import RenameFilesPlugin
    Kind = RenameFilesPlugin


class RenameFiles(EditPane):
    title = _("Rename Files")
    FILTERS = [SpacesToUnderscores, StripWindowsIncompat, StripDiacriticals,
               StripNonASCII, Lowercase]
    handler = RenameFilesPluginHandler()

    def __init__(self, parent, library):
        super(RenameFiles, self).__init__(
            const.NBP, const.NBP_EXAMPLES.split("\n"))

        column = TreeViewColumn(
            _('File'), gtk.CellRendererText(), text=1)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.view.append_column(column)
        render = gtk.CellRendererText()
        render.set_property('editable', True)

        column = TreeViewColumn(_('New Name'), render, text=2)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        self.view.append_column(column)

        self.preview.connect_object('clicked', self.__preview, None)

        parent.connect_object('changed', self.__class__.__preview, self)
        self.save.connect_object('clicked', self.__rename, library)

        render.connect('edited', self.__row_edited)

    def __row_edited(self, renderer, path, new):
        row = self.view.get_model()[path]
        if row[2] != new:
            row[2] = new
            self.preview.set_sensitive(True)
            self.save.set_sensitive(True)

    def __rename(self, library):
        model = self.view.get_model()
        win = WritingWindow(self, len(model))
        was_changed = []
        skip_all = False
        self.view.freeze_child_notify()

        rows = [(row[0], row[1], row[2].decode('utf-8')) for row in model]
        for song, oldname, newname in rows:
            try:
                newname = util.fsnative(newname)
                library.rename(song, newname, changed=was_changed)
            except StandardError:
                util.print_exc()
                if skip_all: continue
                RESPONSE_SKIP_ALL = 1
                buttons = (_("Ignore _All Errors"), RESPONSE_SKIP_ALL,
                           gtk.STOCK_STOP, gtk.RESPONSE_CANCEL,
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
                skip_all |= (resp == RESPONSE_SKIP_ALL)
                # Preserve old behavior: shift-click is Ignore All
                mods = gtk.gdk.display_get_default().get_pointer()[3]
                skip_all |= mods & gtk.gdk.SHIFT_MASK
                library.reload(song, changed=was_changed)
                if resp != gtk.RESPONSE_OK and resp != RESPONSE_SKIP_ALL:
                    break
            if win.step(): break

        self.view.thaw_child_notify()
        win.destroy()
        library.changed(was_changed)
        self.save.set_sensitive(False)

    def __preview(self, songs):
        model = self.view.get_model()
        if songs is None:
            songs = [row[0] for row in model]
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

        orignames = [song["~filename"] for song in songs]
        newnames = [util.fsdecode(util.fsencode(pattern.format(song)))
                    for song in songs]
        for f in self.filters:
            if f.active: newnames = f.filter_list(orignames, newnames)

        model.clear()
        for song, newname in zip(songs, newnames):
            basename = util.fsdecode(song("~basename"))
            model.append(row=[song, basename, newname])
        self.preview.set_sensitive(False)
        self.save.set_sensitive(bool(self.combo.child.get_text()))
        for song in songs:
            if not song.is_file:
                self.set_sensitive(False)
                break
        else: self.set_sensitive(True)
