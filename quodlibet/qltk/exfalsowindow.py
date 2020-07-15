# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from gi.repository import Gtk, GObject, Pango
from senf import fsnative

from quodlibet import ngettext, _
from quodlibet import config
from quodlibet import formats
from quodlibet import qltk
from quodlibet import app

from quodlibet.qltk.appwindow import AppWindow
from quodlibet.formats import AudioFileError
from quodlibet.plugins import PluginManager
from quodlibet.qltk.delete import trash_files, TrashMenuItem
from quodlibet.qltk.edittags import EditTags
from quodlibet.qltk.filesel import MainFileSelector
from quodlibet.qltk.pluginwin import PluginWindow
from quodlibet.qltk.renamefiles import RenameFiles
from quodlibet.qltk.tagsfrompath import TagsFromPath
from quodlibet.qltk.tracknumbers import TrackNumbers
from quodlibet.qltk.menubutton import MenuButton
from quodlibet.qltk.about import AboutDialog
from quodlibet.qltk.songsmenu import SongsMenuPluginHandler
from quodlibet.qltk.x import Align, SeparatorMenuItem, ConfigRHPaned, \
    Button, SymbolicIconImage, MenuItem
from quodlibet.qltk.window import PersistentWindowMixin, Window
from quodlibet.qltk.msg import CancelRevertSave
from quodlibet.qltk.prefs import PreferencesWindow as QLPreferencesWindow
from quodlibet.qltk import Icons
from quodlibet.util.i18n import numeric_phrase
from quodlibet.util.path import mtime, normalize_path
from quodlibet.util import connect_obj, connect_destroy, format_int_locale
from quodlibet.update import UpdateDialog


class ExFalsoWindow(Window, PersistentWindowMixin, AppWindow):

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    pm = SongsMenuPluginHandler()

    @classmethod
    def init_plugins(cls):
        PluginManager.instance.register_handler(cls.pm)

    def __init__(self, library, dir=None):
        super(ExFalsoWindow, self).__init__(dialog=False)
        self.set_title("Ex Falso")
        self.set_default_size(750, 475)
        self.enable_window_tracking("exfalso")

        self.__library = library

        hp = ConfigRHPaned("memory", "exfalso_paned_position", 1.0)
        hp.set_border_width(0)
        hp.set_position(250)
        hp.show()
        self.add(hp)

        vb = Gtk.VBox()

        bbox = Gtk.HBox(spacing=6)

        def prefs_cb(*args):
            window = PreferencesWindow(self)
            window.show()

        def plugin_window_cb(*args):
            window = PluginWindow(self)
            window.show()

        def about_cb(*args):
            about = AboutDialog(self, app)
            about.run()
            about.destroy()

        def update_cb(*args):
            d = UpdateDialog(self)
            d.run()
            d.destroy()

        menu = Gtk.Menu()

        about_item = MenuItem(_("_About"), Icons.HELP_ABOUT)
        about_item.connect("activate", about_cb)
        menu.append(about_item)

        check_item = MenuItem(_("_Check for Updates…"), Icons.NETWORK_SERVER)
        check_item.connect("activate", update_cb)
        menu.append(check_item)

        menu.append(SeparatorMenuItem())

        plugin_item = MenuItem(_("_Plugins"), Icons.SYSTEM_RUN)
        plugin_item.connect("activate", plugin_window_cb)
        menu.append(plugin_item)

        pref_item = MenuItem(_("_Preferences"), Icons.PREFERENCES_SYSTEM)
        pref_item.connect("activate", prefs_cb)
        menu.append(pref_item)

        menu.show_all()

        menu_button = MenuButton(
                SymbolicIconImage(Icons.EMBLEM_SYSTEM, Gtk.IconSize.BUTTON),
                arrow=True, down=False)
        menu_button.set_menu(menu)
        bbox.pack_start(menu_button, False, True, 0)

        l = Gtk.Label()
        l.set_alignment(1.0, 0.5)
        l.set_ellipsize(Pango.EllipsizeMode.END)
        bbox.pack_start(l, True, True, 0)

        self._fs = fs = MainFileSelector()

        vb.pack_start(fs, True, True, 0)
        vb.pack_start(Align(bbox, border=6), False, True, 0)
        vb.show_all()

        hp.pack1(vb, resize=True, shrink=False)

        nb = qltk.Notebook()
        nb.props.scrollable = True
        nb.show()
        for Page in [EditTags, TagsFromPath, RenameFiles, TrackNumbers]:
            page = Page(self, self.__library)
            page.show()
            nb.append_page(page)
        hp.pack2(nb, resize=True, shrink=False)
        fs.connect('changed', self.__changed, l)
        if dir:
            fs.go_to(dir)

        connect_destroy(self.__library, 'changed', self.__library_changed, fs)

        self.__save = None
        connect_obj(self, 'changed', self.set_pending, None)
        for c in fs.get_children():
            c.get_child().connect('button-press-event',
                self.__pre_selection_changed, fs, nb)
            c.get_child().connect('focus',
                                  self.__pre_selection_changed, fs, nb)
        fs.get_children()[1].get_child().connect('popup-menu',
                                                 self.__popup_menu, fs)
        self.emit('changed', [])

        self.get_child().show()

        self.__ag = Gtk.AccelGroup()
        key, mod = Gtk.accelerator_parse("<Primary>Q")
        self.__ag.connect(key, mod, 0, lambda *x: self.destroy())
        self.add_accel_group(self.__ag)

        # GtkosxApplication assumes the menu bar is mapped, so add
        # it but don't show it.
        self._dummy_osx_menu_bar = Gtk.MenuBar()
        vb.pack_start(self._dummy_osx_menu_bar, False, False, 0)

    def __library_changed(self, library, songs, fs):
        fs.rescan()

    def set_as_osx_window(self, osx_app):
        osx_app.set_menu_bar(self._dummy_osx_menu_bar)

    def get_is_persistent(self):
        return False

    def open_file(self, filename):
        assert isinstance(filename, fsnative)

        if not os.path.isdir(filename):
            return False

        self._fs.go_to(filename)

    def set_pending(self, button, *excess):
        self.__save = button

    def __pre_selection_changed(self, view, event, fs, nb):
        if self.__save:
            resp = CancelRevertSave(self).run()
            if resp == Gtk.ResponseType.YES:
                self.__save.clicked()
            elif resp == Gtk.ResponseType.NO:
                fs.rescan()
            else:
                nb.grab_focus()
                return True # cancel or closed

    def __popup_menu(self, view, fs):
        # get all songs for the selection
        filenames = [normalize_path(f, canonicalise=True)
                     for f in fs.get_selected_paths()]
        maybe_songs = [self.__library.get(f) for f in filenames]
        songs = [s for s in maybe_songs if s]

        if songs:
            menu = self.pm.Menu(self.__library, songs)
            if menu is None:
                menu = Gtk.Menu()
            else:
                menu.prepend(SeparatorMenuItem())
        else:
            menu = Gtk.Menu()

        b = TrashMenuItem()
        b.connect('activate', self.__delete, filenames, fs)
        menu.prepend(b)

        def selection_done_cb(menu):
            menu.destroy()

        menu.connect('selection-done', selection_done_cb)
        menu.show_all()
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __delete(self, item, paths, fs):
        trash_files(self, paths)
        fs.rescan()

    def __changed(self, selector, selection, label):
        model, rows = selection.get_selected_rows()
        files = []

        if len(rows) < 2:
            count = len(model or [])
        else:
            count = len(rows)
        label.set_text(numeric_phrase("%d song", "%d songs", count))

        for row in rows:
            filename = model[row][0]
            if not os.path.exists(filename):
                pass
            elif filename in self.__library:
                song = self.__library[filename]
                if song("~#mtime") + 1. < mtime(filename):
                    try:
                        song.reload()
                    except AudioFileError:
                        pass
                files.append(song)
            else:
                files.append(formats.MusicFile(filename))
        files = list(filter(None, files))
        if len(files) == 0:
            self.set_title("Ex Falso")
        elif len(files) == 1:
            self.set_title("%s - Ex Falso" % files[0].comma("title"))
        else:
            params = ({'title': files[0].comma("title"),
                       'count': format_int_locale(len(files) - 1)})
            self.set_title(
                "%s - Ex Falso" %
                (ngettext("%(title)s and %(count)s more",
                          "%(title)s and %(count)s more", len(files) - 1)
                 % params))
        self.__library.add(files)
        self.emit('changed', files)


class PreferencesWindow(QLPreferencesWindow):
    def __init__(self, parent):
        if self.is_not_unique():
            return
        super(QLPreferencesWindow, self).__init__()
        self.set_title(_("Ex Falso Preferences"))
        self.set_border_width(12)
        self.set_resizable(False)
        self.set_transient_for(qltk.get_top_parent(parent))

        tagging = self.Tagging()
        f = qltk.Frame(_("Tag Editing"), child=(tagging.tag_editing_vbox()))

        close = Button(_("_Close"), Icons.WINDOW_CLOSE)
        connect_obj(close, 'clicked', lambda x: x.destroy(), self)
        button_box = Gtk.HButtonBox()
        button_box.set_layout(Gtk.ButtonBoxStyle.END)
        button_box.pack_start(close, True, True, 0)

        main_vbox = Gtk.VBox(spacing=12)
        main_vbox.pack_start(f, True, True, 0)
        self.use_header_bar()
        if not self.has_close_button():
            main_vbox.pack_start(button_box, False, True, 0)
        self.add(main_vbox)

        connect_obj(self, 'destroy', PreferencesWindow.__destroy, self)
        self.get_child().show_all()

    def __destroy(self):
        config.save()
