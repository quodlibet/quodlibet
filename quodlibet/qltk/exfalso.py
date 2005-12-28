# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gtk, gobject

import const
import formats
import qltk
from qltk.filesel import FileSelector
from qltk.delete import DeleteDialog
import qltk.properties

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
        hp = gtk.HPaned()
        hp.set_position(250)
        self.add(hp)
        fs = FileSelector(dir)
        fs.show_all()
        self.child.pack1(fs, resize=True, shrink=False)
        nb = qltk.Notebook()
        nb.show()
        for Page in [qltk.properties.EditTags,
                     qltk.properties.TagByFilename,
                     qltk.properties.RenameFiles,
                     qltk.properties.TrackNumbers]:
            nb.append_page(Page(self, watcher))
        self.child.pack2(nb, resize=True, shrink=False)
        fs.connect('changed', self.__changed)
        self.__cache = {}
        s = watcher.connect_object('refresh', FileSelector.rescan, fs)
        self.connect_object('destroy', watcher.disconnect, s)
        self.__save = None
        self.connect_object('changed', self.set_pending, None)
        for c in fs.get_children():
            c.child.connect('button-press-event', self.__pre_selection_changed)
        fs.get_children()[1].child.connect('popup-menu', self.__popup_menu, fs)
        self.emit('changed', [])

        # plugin support
        self.pm = EFPluginManager(watcher, ["./plugins", const.PLUGINS])
        self.pm.rescan()
        self.child.show()

    def set_pending(self, button, *excess):
        self.__save = button

    def __pre_selection_changed(self, view, event):
        if self.__save:
            resp = qltk.CancelRevertSave(self).run()
            if resp == gtk.RESPONSE_YES: self.__save.clicked()
            elif resp == gtk.RESPONSE_NO: return False
            else: return True # cancel or closed

    def __popup_menu(self, view, fs):
        view.grab_focus()
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        filenames = [model[row][0] for row in rows]
        songs = map(self.__cache.__getitem__, filenames)
        songs.sort()
        menu = self.pm.create_plugins_menu(songs)
        if menu is None: menu = gtk.Menu()
        else: menu.prepend(gtk.SeparatorMenuItem())
        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect('activate', self.__delete, filenames, fs)
        menu.prepend(b)
        menu.show_all()
        menu.popup(None, None, None, 0, gtk.get_current_event_time())
        return True

    def __delete(self, item, files, fs):
        d = DeleteDialog(self, files)
        d.run()
        d.destroy()
        fs.rescan()

    def __changed(self, selector, selection):
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
