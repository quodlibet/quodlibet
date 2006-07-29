# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# Some sort of crazy directory-based browser. QL is full of minor hacks
# to support this by automatically adding songs to the library when it
# needs them to be there.

import os

import gobject
import gtk

import config
import const
import formats
import qltk

from browsers._base import Browser
from library import SongFileLibrary
from qltk.filesel import DirectoryTree
from qltk.songsmenu import SongsMenu

class FileSystem(Browser, gtk.ScrolledWindow):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RHPaned
    __library = None

    name = _("File System")
    accelerated_name = _("_File System")
    priority = 10

    __fill_id = None

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

    def __init__(self, library, player):
        super(FileSystem, self).__init__()
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_IN)

        folders = filter(None, config.get("settings", "scan").split(":"))
        if folders:
            folders.append(None)
        if const.HOME not in folders:
            folders.append(const.HOME)
        if "/" not in folders:
            folders.append("/")

        dt = DirectoryTree(initial=const.HOME, folders=folders)
        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1),
                   ("text/uri-list", 0, 2)]
        dt.drag_source_set(gtk.gdk.BUTTON1_MASK, targets, gtk.gdk.ACTION_COPY)
        dt.connect('drag-data-get', self.__drag_data_get)

        sel = dt.get_selection()
        sel.unselect_all()
        sel.connect('changed', self.__songs_selected)
        if player: dt.connect('row-activated', self.__play, player)
        else: self.save = lambda: None
        self.add(dt)
        self.show_all()

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

    def __play(self, view, indices, column, player):
        player.reset()

    def can_filter(self, key):
        return (key == "~dirname")

    def filter(self, key, values):
        self.child.get_selection().unselect_all()
        for v in values: self.child.go_to(v)

    def restore(self):
        try: paths = config.get("browsers", "filesystem").split("\n")
        except: pass
        else:
            self.child.get_selection().unselect_all()
            for path in paths: self.child.go_to(path)

    def save(self):
        model, rows = self.child.get_selection().get_selected_rows()
        paths = "\n".join([model[row][0] for row in rows])
        config.set("browsers", "filesystem", paths)

    def activate(self):
        self.__songs_selected(self.child.get_selection())

    def Menu(self, songs, songlist, library):
        menu = SongsMenu(library, songs, remove=self.__remove_songs,
                         delete=True, accels=songlist.accelerators)
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
            for file in filter(formats.filter, sorted(os.listdir(dir))):
                fn = os.path.realpath(os.path.join(dir, file))
                if fn in self.__glibrary:
                    songs.append(self.__glibrary[fn])
                elif fn not in self.__library:
                    song = formats.MusicFile(fn)
                    if song:
                        to_add.append(song)
                        songs.append(song)
                if fn in self.__library:
                    song = self.__library[fn]
                    if not song.valid():
                        self.__library.reload(song)
                    if song in self.__library:
                        songs.append(song)
            if not len(to_add) & 0x7:
                yield songs
        self.__library.add(to_add)
        yield songs

    def __songs_selected(self, selection):
        if self.__fill_id is not None:
            gobject.source_remove(self.__fill_id)
        def songs_selected_iter():
            if self.window:
                self.window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
            for songs in self.__find_songs(selection):
                yield True
            if self.window:
                self.window.set_cursor(None)
            self.emit('songs-selected', songs, None)
            yield False
        self.save()
        self.__fill_id = gobject.idle_add(
            songs_selected_iter().next, priority=gobject.PRIORITY_LOW)

browsers = [FileSystem]
