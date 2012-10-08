# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

# Some sort of crazy directory-based browser. QL is full of minor hacks
# to support this by automatically adding songs to the library when it
# needs them to be there.

import os

import gtk

from quodlibet import config
from quodlibet import formats
from quodlibet import qltk

from quodlibet import util
from quodlibet.browsers._base import Browser
from quodlibet.library import SongFileLibrary
from quodlibet.qltk.filesel import DirectoryTree
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.x import ScrolledWindow
from quodlibet.util import copool, split_scan_dirs

class FileSystem(Browser, gtk.HBox):
    __gsignals__ = Browser.__gsignals__

    expand = qltk.RHPaned
    __library = None

    name = _("File System")
    accelerated_name = _("_File System")
    priority = 10

    def __added(klass, library, songs):
        klass.__library.remove(songs)
    __added = classmethod(__added)

    @classmethod
    def init(klass, library):
        klass.__glibrary = library
        klass.__library = SongFileLibrary("filesystem")
        library.connect('added', klass.__remove_because_added)

    @classmethod
    def __remove_because_added(klass, library, songs):
        songs = filter(klass.__library.__contains__, songs)
        klass.__library.remove(songs)

    def __init__(self, library, main):
        super(FileSystem, self).__init__()
        sw = ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)

        folders = filter(None, split_scan_dirs(config.get("settings", "scan")))

        dt = DirectoryTree(folders=folders)
        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        dt.drag_source_set(gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        dt.connect('drag-data-get', self.__drag_data_get)

        sel = dt.get_selection()
        sel.unselect_all()
        sel.connect_object('changed', copool.add, self.__songs_selected, dt)
        if main:
            dt.connect('row-activated', lambda *a: self.emit("activated"))
        sw.add(dt)
        self.pack_start(sw)
        self.show_all()

    @property
    def child(self):
        return self.get_children()[0].get_child()

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        for songs in self.__find_songs(view.get_selection()):
            pass
        if tid == 1:
            cant_add = filter(lambda s: not s.can_add, songs)
            if cant_add:
                qltk.ErrorMessage(
                    qltk.get_top_parent(self), _("Unable to copy songs"),
                    _("The files selected cannot be copied to other "
                      "song lists or the queue.")).run()
                ctx.drag_abort(etime)
                return
            to_add = filter(self.__library.__contains__, songs)
            self.__add_songs(view, to_add)
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
        else:
            uris = [song("~uri") for song in songs]
            sel.set_uris(uris)

    def can_filter_tag(self, key):
        return (key == "~dirname")

    def filter(self, key, values):
        self.child.get_selection().unselect_all()
        for v in values: self.child.go_to(v)

    def scroll(self, song):
        self.__select_paths([song("~dirname")])

    def restore(self):
        try:
            paths = config.get("browsers", "filesystem").split("\n")
        except config.error:
            pass
        else:
            self.__select_paths(paths)

    def __select_paths(self, paths):
        def select(model, path, iter, (paths, first)):
            if model[iter][0] in paths:
                self.child.get_selection().select_path(path)
                paths.remove(model[iter][0])
                if not first:
                    self.child.set_cursor(path)
                    first.append(path)
            else:
                for fpath in paths:
                    if model[path][0] and fpath.startswith(model[path][0]):
                        self.child.expand_row(path, False)
            return not bool(paths)
        first = []
        self.child.get_model().foreach(select, (paths, first))
        if first: self.child.scroll_to_cell(first[0], None, True, 0.5)

    def save(self):
        model, rows = self.child.get_selection().get_selected_rows()
        paths = "\n".join([model[row][0] for row in rows])
        config.set("browsers", "filesystem", paths)

    def activate(self):
        copool.add(self.__songs_selected, self.child)

    def Menu(self, songs, songlist, library):
        menu = SongsMenu(library, songs, remove=self.__remove_songs,
                         delete=True, accels=songlist.accelerators,
                         parent=self)
        i = qltk.MenuItem(_("_Add to Library"), gtk.STOCK_ADD)
        i.set_sensitive(False)
        i.connect('activate', self.__add_songs, songs)
        for song in songs:
            if song not in self.__glibrary:
                i.set_sensitive(True)
                break
        menu.preseparate()
        menu.prepend(i)
        return menu

    def __add_songs(self, item, songs):
        songs = filter(self.__library.__contains__, songs)
        self.__library.librarian.move(songs, self.__library, self.__glibrary)

    def __remove_songs(self, songs):
        songs = filter(self.__glibrary.__contains__, songs)
        self.__library.librarian.move(songs, self.__glibrary, self.__library)

    def __find_songs(self, selection):
        model, rows = selection.get_selected_rows()
        dirs = [model[row][0] for row in rows]
        songs = []
        to_add = []
        for dir in dirs:
            try:
                for file in filter(formats.filter,
                                   sorted(os.listdir(util.fsnative(dir)))):
                    fn = os.path.realpath(os.path.join(dir, file))
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
            except OSError: pass
        self.__library.add(to_add)
        yield songs

    def __songs_selected(self, view):
        if self.window:
            self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
        for songs in self.__find_songs(view.get_selection()):
            yield True
        if self.window:
            self.window.set_cursor(None)
        self.emit('songs-selected', songs, None)

browsers = [FileSystem]
