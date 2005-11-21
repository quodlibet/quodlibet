# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import shutil
import dircache
import gtk, gobject

import const
import formats
import qltk
from qltk.filesel import FileSelector
import util

from properties import SongProperties
from plugins import PluginManager

class EFPluginManager(PluginManager):
    # Ex Falso doesn't send events; it also should enable all
    # invokable plugins since there's no configuration.
    def rescan(self):
        super(EFPluginManager, self).rescan()
        for plugin in self.plugins.values(): self.enable(plugin, True)
        return []

    def invoke_event(self, event, *args): pass

class ExFalsoWindow(gtk.Window):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    def __init__(self, watcher, dir=None):
        gtk.Window.__init__(self)
        self.set_title("Ex Falso")
        self.set_border_width(12)
        self.set_default_size(700, 500)
        self.add(gtk.HPaned())
        fs = FileSelector(dir)
        self.child.pack1(fs, resize=True)
        nb = qltk.Notebook()
        nb.append_page(SongProperties.Information(self, library=False))
        for Page in [SongProperties.EditTags,
                     SongProperties.TagByFilename,
                     SongProperties.RenameFiles,
                     SongProperties.TrackNumbers]:
            nb.append_page(Page(self, watcher))
        self.child.pack2(nb, resize=False, shrink=False)
        fs.connect('changed', self.__changed, nb)
        self.__cache = {}
        s = watcher.connect_object('refresh', FileSelector.rescan, fs)
        self.connect_object('destroy', watcher.disconnect, s)
        self.__save = None
        self.connect_object('changed', self.set_pending, None)
        for c in fs.get_children():
            c.child.connect('button-press-event', self.__pre_selection_changed)
        fs.get_children()[1].child.connect(
            'button-press-event', self.__button_press, fs)
        fs.get_children()[1].child.connect(
            'popup-menu', self.__popup_menu, fs)
        self.emit('changed', [])

        # plugin support
        self.pm = EFPluginManager(watcher, ["./plugins", const.PLUGINS])
        self.pm.rescan()

    def set_pending(self, button, *excess):
        self.__save = button

    def __pre_selection_changed(self, view, event):
        if self.__save:
            resp = qltk.CancelRevertSave(self).run()
            if resp == gtk.RESPONSE_YES: self.__save.clicked()
            elif resp == gtk.RESPONSE_NO: return False
            else: return True # cancel or closed

    def __button_press(self, view, event, fs):
        if event.button == 3:
            x, y = map(int, [event.x, event.y])
            try: path, col, cellx, celly = view.get_path_at_pos(x, y)
            except TypeError: return True
            selection = view.get_selection()
            if not selection.path_is_selected(path):
                view.set_cursor(path, col, 0)
            return self.__show_menu(view, fs, event.button, event.time)

    def __popup_menu(self, view, fs):
        return self.__show_menu(view, fs)

    def __show_menu(self, view, fs, button=1, time=0):
        view.grab_focus()
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        songs = [self.__cache[model[row][0]] for row in rows]
        menu = self.pm.create_plugins_menu(songs)
        if menu is None: menu = gtk.Menu()
        else: menu.prepend(gtk.SeparatorMenuItem())
        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect('activate', self.__delete,
                  [model[row][0] for row in rows], fs)
        menu.prepend(b)
        menu.show_all()
        menu.popup(None, None, None, button, time)
        return True

    def __delete(self, item, files, fs):
        d = qltk.DeleteDialog(files)
        resp = d.run()
        d.destroy()

        # FIXME: Largely copy/paste from SongList.
        if resp == 1 or resp == gtk.RESPONSE_DELETE_EVENT: return
        else:
            if resp == 0: s = _("Moving %d/%d.")
            elif resp == 2: s = _("Deleting %d/%d.")
            else: return
            w = qltk.WaitLoadWindow(None, len(files), s, (0, len(files)))
            trash = os.path.expanduser("~/.Trash")
            for filename in files:
                try:
                    if resp == 0:
                        basename = os.path.basename(filename)
                        shutil.move(filename, os.path.join(trash, basename))
                    else:
                        os.unlink(filename)

                except:
                    qltk.ErrorMessage(
                        self, _("Unable to delete file"),
                        _("Deleting <b>%s</b> failed. "
                          "Possibly the target file does not exist, "
                          "or you do not have permission to "
                          "delete it.") % (filename)).run()
                    break
                else:
                    w.step(w.current + 1, w.count)
            w.destroy()
            fs.rescan()

    def __changed(self, selector, selection, notebook):
        model, rows = selection.get_selected_rows()
        files = []
        for row in rows:
            filename = model[row][0]
            if not os.path.exists(filename): pass
            elif filename in self.__cache: files.append(self.__cache[filename])
            else: files.append(formats.MusicFile(model[row][0]))
        files = filter(None, files)
        self.emit('changed', files)
        self.__cache.clear()
        if len(files) == 0: self.set_title("Ex Falso")
        elif len(files) == 1:
            self.set_title("%s - Ex Falso" % files[0].comma("title"))
        else:
            self.set_title("%s - Ex Falso" % (_("%(title)s and %(count)d more")
                % {'title': files[0].comma("title"), 'count': len(files) - 1}))
        self.__cache = dict([(song["~filename"], song) for song in files])

gobject.type_register(ExFalsoWindow)
