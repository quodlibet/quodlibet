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
from quodlibet import util

from quodlibet.plugins import PluginManager
from quodlibet.qltk.ccb import ConfigCheckButton
from quodlibet.qltk.delete import DeleteDialog
from quodlibet.qltk.edittags import EditTags
from quodlibet.qltk.filesel import FileSelector
from quodlibet.qltk.pluginwin import PluginWindow
from quodlibet.qltk.renamefiles import RenameFiles
from quodlibet.qltk.tagsfrompath import TagsFromPath
from quodlibet.qltk.tracknumbers import TrackNumbers
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk.about import AboutExFalso
from quodlibet.qltk.songsmenu import SongsMenuPluginHandler
from quodlibet.qltk.x import Alignment
from quodlibet.qltk.window import PersistentWindowMixin


class ExFalsoWindow(gtk.Window, PersistentWindowMixin):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,)),

                     'artwork-changed': (gobject.SIGNAL_RUN_LAST,
                                         gobject.TYPE_NONE, (object,))
                     }

    pm = SongsMenuPluginHandler()

    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.pm)

    def __init__(self, library, dir=None):
        super(ExFalsoWindow, self).__init__()
        self.set_title("Ex Falso")
        self.set_default_size(650, 475)
        self.enable_window_tracking("exfalso")

        self.__library = library

        hp = gtk.HPaned()
        hp.set_border_width(0)
        hp.set_position(250)
        hp.show()
        self.add(hp)

        vb = gtk.VBox()

        bbox = gtk.HBox(spacing=6)

        about = gtk.Button()
        about.add(gtk.image_new_from_stock(
            gtk.STOCK_ABOUT, gtk.ICON_SIZE_BUTTON))
        about.connect_object('clicked', self.__show_about, self)
        bbox.pack_start(about, expand=False)

        prefs = gtk.Button()
        prefs.add(gtk.image_new_from_stock(
            gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_BUTTON))
        prefs.connect_object('clicked', PreferencesWindow, self)
        bbox.pack_start(prefs, expand=False)

        plugins = qltk.Button(_("_Plugins"), gtk.STOCK_EXECUTE)
        plugins.connect_object('clicked', PluginWindow, self)
        bbox.pack_start(plugins, expand=False)

        l = gtk.Label()
        l.set_alignment(1.0, 0.5)
        l.set_ellipsize(pango.ELLIPSIZE_END)
        bbox.pack_start(l)

        fs = FileSelector(dir)

        vb.pack_start(fs)
        vb.pack_start(Alignment(bbox, border=6), expand=False)
        vb.show_all()

        hp.pack1(vb, resize=True, shrink=False)

        nb = qltk.Notebook()
        nb.show()
        for Page in [EditTags, TagsFromPath, RenameFiles, TrackNumbers]:
            nb.append_page(Page(self, self.__library))
        align = Alignment(nb, top=3)
        align.show()
        hp.pack2(align, resize=True, shrink=False)
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
        self.__ag.connect_group(key, mod, 0, lambda *x: self.destroy())
        self.add_accel_group(self.__ag)

    def __show_about(self, window):
        about = AboutExFalso(self)
        about.run()
        about.destroy()

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
        e = UndoEntry()
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

        close = gtk.Button(stock=gtk.STOCK_CLOSE)
        close.connect_object('clicked', lambda x: x.destroy(), self)
        button_box = gtk.HButtonBox()
        button_box.set_layout(gtk.BUTTONBOX_END)
        button_box.pack_start(close)

        main_vbox = gtk.VBox(spacing=12)
        main_vbox.pack_start(f)
        main_vbox.pack_start(button_box, expand=False)
        self.add(main_vbox)

        self.connect_object('destroy', PreferencesWindow.__destroy, self)
        self.show_all()

    def __changed(self, entry, section, name):
        config.set(section, name, entry.get_text())

    def __destroy(self):
        config.write(const.CONFIG)
