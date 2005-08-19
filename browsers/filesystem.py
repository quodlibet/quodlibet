# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# FIXME: Files not in the library tend to do bad things:
# - Renaming breaks QL
# - Attempting to remove causes KeyErrors
# - DnD doesn't work since we exchange filenames
# Mostly, I'm surprised they work at all.

import os
import gobject, gtk
import const
import qltk
import util
import parser
import config
import formats
from efwidgets import DirectoryTree

from browsers.base import Browser
from library import library

class Filesystem(Browser, gtk.ScrolledWindow):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RHPaned

    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_IN)
        dt = DirectoryTree(initial=os.environ["HOME"])
        sel = dt.get_selection()
        sel.connect('changed', self.__find_songs)
        self.add(dt)
        self.show_all()

    def restore(self): pass

    def __find_songs(self, selection):
        model, rows = selection.get_selected_rows()
        dirs = [model[row][0] for row in rows]
        songs = []
        for dir in dirs:
            for file in filter(formats.filter, os.listdir(dir)):
                fn = os.path.join(dir, file)
                if fn in library: songs.append(library[fn])
                else:
                    song = formats.MusicFile(fn)
                    if song is not None: songs.append(song)
        self.emit('songs-selected', songs, None)

gobject.type_register(Filesystem)
browsers = [(10, _("_Filesystem"), Filesystem, True)]
