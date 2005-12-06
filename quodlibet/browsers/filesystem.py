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
import gobject, gtk
import qltk
import formats
import config

from browsers.base import Browser
from library import Library, library as glibrary
from qltk.filesel import DirectoryTree

class FileSystem(Browser, gtk.ScrolledWindow):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RHPaned
    __lib = Library()

    def __init__(self, watcher, player):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_IN)
        dt = DirectoryTree(initial=os.environ["HOME"])
        sel = dt.get_selection()
        sel.unselect_all()
        sel.connect('changed', self.__find_songs)
        if player: dt.connect('row-activated', self.__play, player)
        self.__save = bool(player)
        self.add(dt)
        self.__refresh_library()
        self.show_all()

    def __refresh_library(self):
        for fn, song in self.__lib.items():
            if fn in glibrary: self.__lib.remove(song)
            elif not song.valid(): self.__lib.reload(song)

    def __play(self, view, indices, column, player):
        player.reset()
        player.next()

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
        self.__find_songs(self.child.get_selection())

    def Menu(self, songs, songlist):
        m = gtk.Menu()
        i = qltk.MenuItem(_("_Add to Library"), gtk.STOCK_ADD)
        i.set_sensitive(False)
        i.connect('activate', self.__add_songs, songs)
        for song in songs:
            if song["~filename"] not in glibrary:
                i.set_sensitive(True)
                break
        m.append(i)
        return m

    def __add_songs(self, item, songs):
        added = []
        for song in songs:
            if song["~filename"] not in glibrary:
                glibrary[song["~filename"]] = song
                added.append(song)
        self.__refresh_library()
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

        if self.__save: self.save()
        self.emit('songs-selected', songs, None)

gobject.type_register(FileSystem)
browsers = [(10, _("_File System"), FileSystem, True)]
