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

import gtk

import formats
import config
import qltk

from browsers._base import Browser
from library import Library, library as glibrary
from qltk.filesel import DirectoryTree

class FileSystem(Browser, gtk.ScrolledWindow):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RHPaned
    __lib = None

    def __added(klass, watcher, songs):
        map(klass.__lib.remove, songs)
    __added = classmethod(__added)

    def __init__(self, watcher, player):
        super(FileSystem, self).__init__()
        if self.__lib is None:
            FileSystem.__lib = Library()
            watcher.connect('added', FileSystem.__added)

        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_IN)
        dt = DirectoryTree(initial=os.environ["HOME"])
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
        songs = self.__find_songs(view.get_selection())
        if tid == 1:
            cant_add = filter(lambda s: not s.can_add, songs)
            if cant_add:
                qltk.ErrorMessage(
                    qltk.get_top_parent(self), _("Unable to copy songs"),
                    _("The files selected cannot be copied to other "
                      "song lists or the queue.")).run()
                ctx.drag_abort(etime)
                return
            self.__add_songs(view, songs)
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

    def Menu(self, songs, songlist):
        m = gtk.Menu()
        i = qltk.MenuItem(_("_Add to Library"), gtk.STOCK_ADD)
        i.set_sensitive(False)
        i.connect('activate', self.__add_songs, songs)
        for song in songs:
            if song["~filename"] not in glibrary:
                i.set_sensitive(True)
                break
        return [i]

    def __add_songs(self, item, songs):
        added = []
        for song in songs:
            if song["~filename"] not in glibrary:
                glibrary[song["~filename"]] = song
                added.append(song)
        if added:
            from widgets import watcher
            watcher.added(added)

    def __find_songs(self, selection):
        model, rows = selection.get_selected_rows()
        dirs = [model[row][0] for row in rows]
        songs = []
        for dir in dirs:
            for file in filter(formats.filter, os.listdir(dir)):
                fn = os.path.realpath(os.path.join(dir, file))
                if fn in glibrary: songs.append(glibrary[fn])
                elif fn not in self.__lib:
                    song = formats.MusicFile(fn)
                    if song: self.__lib[song["~filename"]] = song
                if fn in self.__lib:
                    if not self.__lib[fn].valid():
                        self.__lib.reload(self.__lib[fn])
                    if fn in self.__lib: songs.append(self.__lib[fn])
        return songs

    def __songs_selected(self, selection):
        songs = self.__find_songs(selection)
        self.save()
        self.emit('songs-selected', songs, None)

browsers = [(10, _("_File System"), FileSystem, True)]
