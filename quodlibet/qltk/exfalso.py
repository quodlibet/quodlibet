# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gobject
import gtk
import pango

import config
import const
import formats
import qltk
import stock

from qltk.ccb import ConfigCheckButton
from qltk.delete import DeleteDialog
from qltk.edittags import EditTags
from qltk.filesel import FileSelector
from qltk.pluginwin import PluginWindow
from qltk.renamefiles import RenameFiles
from qltk.tagsfrompath import TagsFromPath
from qltk.tracknumbers import TrackNumbers
from plugins.editing import EditingPlugins
from plugins.songsmenu import SongsMenuPlugins

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
            [os.path.join(const.BASEDIR, "plugins", "songsmenu"),
             os.path.join(const.USERDIR, "plugins", "songsmenu")], "songsmenu")
        self.pm.rescan()

        self.plugins = EditingPlugins(
            [os.path.join(const.BASEDIR, "plugins", "editing"),
             os.path.join(const.USERDIR, "plugins", "editing")], "editing")
        self.plugins.rescan()

        hp = gtk.HPaned()
        hp.set_border_width(6)
        hp.set_position(250)
        hp.show()
        self.add(hp)

        vb = gtk.VBox(spacing=6)

        bbox = gtk.HBox(spacing=6)
        prefs = gtk.Button()
        prefs.add(gtk.image_new_from_stock(
            gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_BUTTON))
        prefs.connect_object('clicked', PreferencesWindow, self)
        bbox.pack_start(prefs, expand=False)
        plugins = gtk.Button(stock=stock.PLUGINS)
        plugins.connect_object('clicked', PluginWindow, self)
        bbox.pack_start(plugins, expand=False)

        l = gtk.Label()
        l.set_justify(gtk.JUSTIFY_RIGHT)
        l.set_ellipsize(pango.ELLIPSIZE_END)
        bbox.pack_start(l)

        fs = FileSelector(dir)

        vb.pack_start(fs)
        vb.pack_start(bbox, expand=False)
        vb.show_all()

        hp.pack1(vb, resize=True, shrink=False)

        nb = qltk.Notebook()
        nb.show()
        for Page in [EditTags, TagsFromPath, RenameFiles, TrackNumbers]:
            nb.append_page(Page(self, watcher))
        hp.pack2(nb, resize=True, shrink=False)
        fs.connect('changed', self.__changed, l)
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

        ag = gtk.AccelGroup()
        key, mod = gtk.accelerator_parse("<control>Q")
        ag.connect_group(key, mod, 0, gtk.main_quit)
        self.add_accel_group(ag)

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
        filenames = sorted([model[row][0] for row in rows])
        songs = map(self.__cache.__getitem__, filenames)
        menu = self.pm.Menu(self.__watcher, self, songs)
        if menu is None: menu = gtk.Menu()
        else: menu.prepend(gtk.SeparatorMenuItem())
        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect('activate', self.__delete, filenames, fs)
        menu.prepend(b)
        menu.connect_object('selection-done', gtk.Menu.destroy, menu)
        menu.show_all()
        return view.popup_menu(menu, 0, gtk.get_current_event_time()) 

    def __delete(self, item, files, fs):
        d = DeleteDialog(self, files)
        d.run()
        d.destroy()
        fs.rescan()

    def __changed(self, selector, selection, label):
        model, rows = selection.get_selected_rows()
        files = []

        if len(rows) < 2: count = len(model or [])
        else: count = len(rows)
        label.set_text(ngettext("%d song", "%d songs", count) % count)

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

class PreferencesWindow(qltk.Window):
    __window = None

    def __new__(klass, parent):
        if klass.__window is None:
            return super(PreferencesWindow, klass).__new__(klass)
        else: return klass.__window

    def __init__(self, parent):
        if type(self).__window: return
        else: type(self).__window = self
        super(PreferencesWindow, self).__init__()
        self.set_title(_("Ex Falso Preferences"))
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(parent)

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
        f = qltk.Frame(_("Tag Editing"), child=vbox)
        self.add(f)

        self.connect_object('destroy', PreferencesWindow.__destroy, self)
        self.show_all()

    def __changed(self, entry, section, name):
        config.set(section, name, entry.get_text())

    def __destroy(self):
        type(self).__window = None
        config.write(const.CONFIG)
