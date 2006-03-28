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
import config
import stock
import formats
import qltk

from qltk.ccb import ConfigCheckButton
from qltk.filesel import FileSelector
from qltk.delete import DeleteDialog
from qltk.edittags import EditTags
from qltk.tagsfrompath import TagsFromPath
from qltk.renamefiles import RenameFiles
from qltk.tracknumbers import TrackNumbers

from plugins.editing import EditingPlugins
from plugins.songsmenu import SongsMenuPlugins

from qltk.pluginwin import PluginWindow

class ExFalsoWindow(gtk.Window):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    def __init__(self, watcher, dir=None):
        super(ExFalsoWindow, self).__init__()
        self.set_title("Ex Falso")
        self.set_default_size(700, 500)

        # plugin support
        self.__watcher = watcher
        self.pm = SongsMenuPlugins(
            [os.path.join("./plugins", "songsmenu"),
             os.path.join(const.PLUGINS, "songsmenu")], "songsmenu")
        self.pm.rescan()

        self.plugins = EditingPlugins(
            [os.path.join("./plugins", "editing"),
             os.path.join(const.PLUGINS, "editing")], "editing")
        self.plugins.rescan()
        self.add(gtk.VBox())
        self.__setup_menubar()

        hp = gtk.HPaned()
        hp.set_border_width(6)
        hp.set_position(250)
        hp.show()
        self.child.pack_start(hp)
        fs = FileSelector(dir)
        fs.show_all()
        hp.pack1(fs, resize=True, shrink=False)
        nb = qltk.Notebook()
        nb.show()
        for Page in [EditTags, TagsFromPath, RenameFiles, TrackNumbers]:
            nb.append_page(Page(self, watcher))
        hp.pack2(nb, resize=True, shrink=False)
        fs.connect('changed', self.__changed)
        self.__cache = {}
        s = watcher.connect_object('changed', FileSelector.rescan, fs)
        self.connect_object('destroy', watcher.disconnect, s)
        self.__save = None
        self.connect_object('changed', self.set_pending, None)
        for c in fs.get_children():
            c.child.connect('button-press-event', self.__pre_selection_changed)
        fs.get_children()[1].child.connect('popup-menu', self.__popup_menu, fs)
        self.emit('changed', [])

        self.child.show()

    def __setup_menubar(self):
        ag = gtk.AccelGroup()

        mb = gtk.MenuBar()
        music = gtk.MenuItem(_("_Music"))

        submenu = gtk.Menu()
        item = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES, ag)
        item.connect_object('activate', PreferencesWindow, self)
        submenu.append(item)
        item = gtk.ImageMenuItem(stock.PLUGINS, ag)
        item.connect_object('activate', PluginWindow, self)
        submenu.append(item)
        submenu.append(gtk.SeparatorMenuItem())
        item = gtk.ImageMenuItem(gtk.STOCK_QUIT, ag)
        item.connect('activate', gtk.main_quit)
        submenu.append(item)
        music.set_submenu(submenu)

        mb.append(music)

        mb.show_all()
        self.add_accel_group(ag)
        self.child.pack_start(mb, expand=False)

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
        menu = self.pm.Menu(self.__watcher, self, songs)
        if menu is None: menu = gtk.Menu()
        else: menu.prepend(gtk.SeparatorMenuItem())
        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect('activate', self.__delete, filenames, fs)
        menu.prepend(b)
        menu.connect_object('selection-done', gtk.Menu.destroy, menu)
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

class PreferencesWindow(gtk.Window):
    __window = None

    def __new__(klass, parent):
        if klass.__window is None:
            return super(PreferencesWindow, klass).__new__(klass)
        else: return klass.__window

    def __init__(self, parent):
        if type(self).__window: return
        else: type(self).__window = self
        super(PreferencesWindow, self).__init__()
        # FIXME: Change to "Ex Falso Preferences" after 0.19.
        self.set_title(_("Preferences"))
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(parent)

        f = qltk.Frame(_("Tag Editing"), bold=True)
        vbox = gtk.VBox(spacing=6)
        hb = gtk.HBox(spacing=6)
        e = gtk.Entry()
        e.set_text(config.get("editing", "split_on"))
        e.connect('changed', self.__changed, 'editing', 'split_on')
        l = gtk.Label(_("Split _on:"))
        l.set_use_underline(True)
        l.set_mnemonic_widget(e)
        hb.pack_start(l, expand=False)
        hb.pack_start(e)
        cb = ConfigCheckButton(
            _("Show _programmatic tags"), 'editing', 'alltags')
        cb.set_active(config.getboolean("editing", 'alltags'))
        vbox.pack_start(hb, expand=False)
        vbox.pack_start(cb, expand=False)
        f.child.add(vbox)
        self.add(f)

        self.connect_object('destroy', PreferencesWindow.__destroy, self)
        self.show_all()

    def __changed(self, entry, section, name):
        config.set(section, name, entry.get_text())

    def __destroy(self):
        type(self).__window = None
        config.write(const.CONFIG)
