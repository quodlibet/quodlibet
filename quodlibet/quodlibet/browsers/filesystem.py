# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012,2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# Some sort of crazy directory-based browser. QL is full of minor hacks
# to support this by automatically adding songs to the library when it
# needs them to be there.

import os

from gi.repository import Gtk, Gdk
from senf import fsn2uri, fsn2bytes, bytes2fsn

from quodlibet import config
from quodlibet import formats
from quodlibet import qltk
from quodlibet import _
from quodlibet.browsers import Browser
from quodlibet.library import SongFileLibrary
from quodlibet.qltk.filesel import MainDirectoryTree
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.x import ScrolledWindow
from quodlibet.qltk import Icons
from quodlibet.util import copool
from quodlibet.util.library import get_scan_dirs
from quodlibet.util.dprint import print_d
from quodlibet.util.path import normalize_path
from quodlibet.util import connect_obj


class FileSystem(Browser, Gtk.HBox):

    __library = None

    name = _("File System")
    accelerated_name = _("_File System")
    keys = ["FileSystem"]
    priority = 10
    uses_main_library = False

    TARGET_QL, TARGET_EXT = range(1, 3)

    def pack(self, songpane):
        container = qltk.ConfigRHPaned("browsers", "filesystem_pos", 0.4)
        container.pack1(self, True, False)
        container.pack2(songpane, True, False)
        return container

    def unpack(self, container, songpane):
        container.remove(songpane)
        container.remove(self)

    @classmethod
    def __added(klass, library, songs):
        klass.__library.remove(songs)

    @classmethod
    def init(klass, library):
        if klass.__library is not None:
            return

        klass.__glibrary = library
        klass.__library = SongFileLibrary("filesystem")
        library.connect('added', klass.__remove_because_added)

    @classmethod
    def __remove_because_added(klass, library, songs):
        songs = list(filter(klass.__library.__contains__, songs))
        klass.__library.remove(songs)

    def __init__(self, library):
        super(FileSystem, self).__init__()
        sw = ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)

        dt = MainDirectoryTree(folders=get_scan_dirs())
        targets = [("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP,
                    self.TARGET_QL),
                   ("text/uri-list", 0, self.TARGET_EXT)]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        dt.drag_source_set(Gdk.ModifierType.BUTTON1_MASK,
                           targets, Gdk.DragAction.COPY)
        dt.connect('drag-data-get', self.__drag_data_get)

        sel = dt.get_selection()
        sel.unselect_all()
        connect_obj(sel, 'changed', copool.add, self.__songs_selected, dt)
        sel.connect("changed", self._on_selection_changed)
        dt.connect('row-activated', lambda *a: self.songs_activated())
        sw.add(dt)
        self.pack_start(sw, True, True, 0)

        self.show_all()

    def _on_selection_changed(self, tree_selection):
        model, rows = tree_selection.get_selected_rows()
        selected_paths = [model[row][0] for row in rows]

        if selected_paths:
            data = fsn2bytes("\n".join(selected_paths), "utf-8")
        else:
            data = b""

        config.setbytes("browsers", "filesystem", data)

    def get_child(self):
        return self.get_children()[0].get_child()

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        model, rows = view.get_selection().get_selected_rows()
        dirs = [model[row][0] for row in rows]
        for songs in self.__find_songs(view.get_selection()):
            pass
        if tid == self.TARGET_QL:
            cant_add = list(filter(lambda s: not s.can_add, songs))
            if cant_add:
                qltk.ErrorMessage(
                    qltk.get_top_parent(self), _("Unable to copy songs"),
                    _("The files selected cannot be copied to other "
                      "song lists or the queue.")).run()
                ctx.drag_abort(etime)
                return
            to_add = list(filter(self.__library.__contains__, songs))
            self.__add_songs(view, to_add)

            qltk.selection_set_songs(sel, songs)
        else:
            # External target (app) is delivered a list of URIS of songs
            uris = list({fsn2uri(dir) for dir in dirs})
            print_d("Directories to drop: %s" % dirs)
            sel.set_uris(uris)

    def can_filter_tag(self, key):
        return key == "~dirname"

    def filter(self, key, values):
        self.get_child().get_selection().unselect_all()
        for v in values:
            self.get_child().go_to(v)

    def scroll(self, song):
        self.__select_paths([song("~dirname")])

    def restore(self):
        data = config.getbytes("browsers", "filesystem", b"")
        try:
            paths = bytes2fsn(data, "utf-8")
        except ValueError:
            return
        if not paths:
            return
        self.__select_paths(paths.split("\n"))

    def __select_paths(self, paths):
        # AudioFile uses normalized paths, DirectoryTree doesn't

        paths = list(map(normalize_path, paths))

        def select(model, path, iter_, paths_):
            (paths, first) = paths_
            value = model.get_value(iter_)
            if value is None:
                return not bool(paths)
            value = normalize_path(value)

            if value in paths:
                self.get_child().get_selection().select_path(path)
                paths.remove(value)
                if not first:
                    self.get_child().set_cursor(path)
                    # copy treepath, gets invalid after the callback
                    first.append(path.copy())
            else:
                for fpath in paths:
                    if fpath.startswith(value):
                        self.get_child().expand_row(path, False)
            return not bool(paths)

        # XXX: We expect all paths we want in DirectoryTree to be
        # expanded once before
        first = []
        self.get_child().get_model().foreach(select, (paths, first))
        if first:
            self.get_child().scroll_to_cell(first[0], None, True, 0.5)

    def activate(self):
        copool.add(self.__songs_selected, self.get_child())

    def Menu(self, songs, library, items):

        i = qltk.MenuItem(_("_Add to Library"), Icons.LIST_ADD)
        i.set_sensitive(False)
        i.connect('activate', self.__add_songs, songs)
        for song in songs:
            if song not in self.__glibrary:
                i.set_sensitive(True)
                break

        items.append([i])
        menu = SongsMenu(library, songs, remove=self.__remove_songs,
                         delete=True, queue=True, items=items)
        return menu

    def __add_songs(self, item, songs):
        songs = list(filter(self.__library.__contains__, songs))
        self.__library.librarian.move(songs, self.__library, self.__glibrary)

    def __remove_songs(self, songs):
        songs = list(filter(self.__glibrary.__contains__, songs))
        self.__library.librarian.move(songs, self.__glibrary, self.__library)

    def __find_songs(self, selection):
        model, rows = selection.get_selected_rows()
        dirs = [model[row][0] for row in rows]
        songs = []
        to_add = []
        for dir in dirs:
            try:
                for file in list(filter(formats.filter,
                                        sorted(os.listdir(dir)))):
                    raw_path = os.path.join(dir, file)
                    fn = normalize_path(raw_path, canonicalise=True)
                    if fn in self.__glibrary:
                        songs.append(self.__glibrary[fn])
                    elif fn not in self.__library:
                        song = formats.MusicFile(fn)
                        if song:
                            to_add.append(song)
                            songs.append(song)
                            yield songs
                    if fn in self.__library:
                        song = self.__library[fn]
                        if not song.valid():
                            self.__library.reload(song)
                        if song in self.__library:
                            songs.append(song)
            except OSError:
                pass
        self.__library.add(to_add)
        yield songs

    def __songs_selected(self, view):
        if self.get_window():
            self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        for songs in self.__find_songs(view.get_selection()):
            yield True
        if self.get_window():
            self.get_window().set_cursor(None)
        self.songs_selected(songs)

browsers = [FileSystem]
