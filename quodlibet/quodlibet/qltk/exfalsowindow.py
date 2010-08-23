# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

import gobject
import gtk
import pango

from quodlibet import config
from quodlibet import const
from quodlibet import formats
from quodlibet import qltk
from quodlibet import stock
from quodlibet import util

from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.delete import DeleteDialog
from quodlibet.qltk.edittags import EditTags
from quodlibet.qltk.filesel import FileSelector
from quodlibet.qltk.pluginwin import PluginWindow
from quodlibet.qltk.renamefiles import RenameFiles
from quodlibet.qltk.tagsfrompath import TagsFromPath
from quodlibet.qltk.tracknumbers import TrackNumbers
from quodlibet.plugins.editing import EditingPlugins
from quodlibet.plugins.songsmenu import SongsMenuPlugins

class ExFalsoWindow(gtk.Window):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    def __init__(self, library, dir=None):
        super(ExFalsoWindow, self).__init__()
        self.set_title("Ex Falso")
        self.set_default_size(700, 500)

        # plugin support
        self.__library = library
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
        l.set_alignment(1.0, 0.5)
        l.set_ellipsize(pango.ELLIPSIZE_END)
        bbox.pack_start(l)
        
        if os.name == "nt":
            # use HOME, Documents (if not under HOME), and non-floppy drives
            folders = [const.HOME]
            try: from win32com.shell import shell, shellcon as con
            except ImportError, e: pass
            else:
                documents = shell.SHGetFolderPath(0, con.CSIDL_PERSONAL, 0, 0)
                if not documents.startswith(const.HOME + os.sep):
                    folders.append(documents)
                music = shell.SHGetFolderPath(0, con.CSIDL_MYMUSIC, 0, 0)
                folders.insert(0, music)
            folders = filter(os.path.isdir, folders +
                [letter + ":\\" for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ"])
        else:
            folders = [const.HOME, "/"]

        fs = FileSelector(dir, folders=folders)

        vb.pack_start(fs)
        vb.pack_start(bbox, expand=False)
        vb.show_all()

        hp.pack1(vb, resize=True, shrink=False)

        nb = qltk.Notebook()
        nb.show()
        for Page in [EditTags, TagsFromPath, RenameFiles, TrackNumbers]:
            nb.append_page(Page(self, self.__library))
        hp.pack2(nb, resize=True, shrink=False)
        fs.connect('changed', self.__changed, l)
        s = self.__library.connect_object('changed', FileSelector.rescan, fs)
        self.connect_object('destroy', self.__library.disconnect, s)
        self.__save = None
        self.connect_object('changed', self.set_pending, None)
        for c in fs.get_children():
            c.child.connect('button-press-event',
                self.__pre_selection_changed, fs, nb)
            c.child.connect('focus', self.__pre_selection_changed, fs, nb)
        fs.get_children()[1].child.connect('popup-menu', self.__popup_menu, fs)
        self.emit('changed', [])

        self.child.show()

        self.__ag = gtk.AccelGroup()
        key, mod = gtk.accelerator_parse("<control>Q")
        self.__ag.connect_group(key, mod, 0, gtk.main_quit)
        self.add_accel_group(self.__ag)

        self.connect('configure-event', ExFalsoWindow.__save_size)
        self.connect('window-state-event', self.__window_state_changed)
        self.__state = 0

        if config.getint("memory", "exfalso_maximized"):
            self.maximize()
        self.resize(*map(int, config.get("memory", "exfalso_size").split()))

    def __window_state_changed(self, window, event):
        self.__state = event.new_window_state
        if self.__state & gtk.gdk.WINDOW_STATE_WITHDRAWN: return
        print int(self.__state & gtk.gdk.WINDOW_STATE_MAXIMIZED)
        if self.__state & gtk.gdk.WINDOW_STATE_MAXIMIZED:
            config.set("memory", "exfalso_maximized", "1")
        else:
            config.set("memory", "exfalso_maximized", "0")

    def __save_size(self, event):
        if not self.__state & gtk.gdk.WINDOW_STATE_MAXIMIZED:
            config.set("memory", "exfalso_size",
                "%d %d" % (event.width, event.height))

    def set_pending(self, button, *excess):
        self.__save = button

    def __pre_selection_changed(self, view, event, fs, nb):
        if self.__save:
            resp = qltk.CancelRevertSave(self).run()
            if resp == gtk.RESPONSE_YES: self.__save.clicked()
            elif resp == gtk.RESPONSE_NO: FileSelector.rescan(fs)
            else:
                nb.grab_focus()
                return True # cancel or closed

    def __popup_menu(self, view, fs):
        view.grab_focus()
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        filenames = sorted([os.path.realpath(model[row][0]) for row in rows])
        songs = map(self.__library.get, filenames)
        if None not in songs:
            menu = self.pm.Menu(self.__library, self, songs)
            if menu is None: menu = gtk.Menu()
            else: menu.prepend(gtk.SeparatorMenuItem())
        else:
            menu = gtk.Menu()
        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect('activate', self.__delete, filenames, fs)
        menu.prepend(b)
        menu.connect_object('selection-done', gtk.Menu.destroy, menu)
        menu.show_all()
        return view.popup_menu(menu, 0, gtk.get_current_event_time()) 

    def __delete(self, item, files, fs):
        d = DeleteDialog(self, files)
        removed = d.run()
        d.destroy()
        removed = filter(None, map(self.__library.get, removed))
        self.__library.remove(removed)
        fs.rescan()

    def __changed(self, selector, selection, label):
        model, rows = selection.get_selected_rows()
        files = []

        if len(rows) < 2: count = len(model or [])
        else: count = len(rows)
        label.set_text(ngettext("%d song", "%d songs", count) % count)

        for row in rows:
            filename = util.fsnative(model[row][0])
            if not os.path.exists(filename): pass
            elif filename in self.__library:
                file = self.__library[filename]
                if file("~#mtime") + 1. < util.mtime(filename):
                    try: file.reload()
                    except StandardError: pass
                files.append(file)
            else: files.append(formats.MusicFile(filename))
        files = filter(None, files)
        if len(files) == 0: self.set_title("Ex Falso")
        elif len(files) == 1:
            self.set_title("%s - Ex Falso" % files[0].comma("title"))
        else:
            self.set_title(
                "%s - Ex Falso" %
                (ngettext("%(title)s and %(count)d more",
                          "%(title)s and %(count)d more",
                          len(files) - 1) % (
                {'title': files[0].comma("title"), 'count': len(files) - 1})))
        self.__library.add(files)
        self.emit('changed', files)

class PreferencesWindow(qltk.UniqueWindow):
    def __init__(self, parent):
        if self.is_not_unique(): return
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
        config.write(const.CONFIG)
