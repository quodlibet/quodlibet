# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys
import urllib
import gobject, gtk
from gettext import ngettext

import const
import qltk
import util
from library import library
from browsers.base import Browser
from widgets import widgets

PLAYLISTS = os.path.join(const.DIR, "playlists")
if not os.path.isdir(PLAYLISTS): util.mkdir(PLAYLISTS)

class Playlist(list):
    quote = staticmethod(lambda text: urllib.quote(text, safe=""))    
    unquote = staticmethod(urllib.unquote)

    def __init__(self, name):
        super(Playlist, self).__init__()
        self.name = name
        basename = self.quote(name)
        try:
            for line in file(os.path.join(PLAYLISTS, basename), "r"):
                if line.rstrip() in library:
                    self.append(library[line.rstrip()])
        except IOError: self.write()

    def rename(self, newname):
        if os.path.exists(os.path.join(PLAYLISTS, self.quote(newname))):
            raise ValueError(
                _("A playlist named %s already exists.") % newname)
        else:
            try: os.unlink(os.path.join(PLAYLISTS, self.quote(self.name)))
            except EnvironmentError: pass
            self.name = newname
            self.write()

    def write(self):
        basename = self.quote(self.name)
        f = file(os.path.join(PLAYLISTS, basename), "w")
        for song in self: f.write(song("~filename"))
        f.close()

    def format(self):
        return "<b>%s</b>\n<small>%s (%s)</small>" % (
            util.escape(self.name),
            ngettext("%d song", "%d songs", len(self)) % len(self),
            util.format_time(sum([t.get("~#length") for t in self])))

    def __cmp__(self, other): return cmp(self.name, other.name)

class Playlists(gtk.VBox, Browser):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RHPaned
    __lists = gtk.ListStore(object)

    def init(klass):
        for playlist in os.listdir(PLAYLISTS):
            __lists.append(row=[Playlist.unquote(playlist)])
        widgets.watcher.connect('removed', klass.__removed)
    init = classmethod(init)

    def __removed(klass, watcher, songs):
        for row in klass.__lists:
            playlist = row[0]
            changed = False
            for song in songs:
                index = playlist.find(song)
                while index >= 0:
                    changed = True
                    del(playlist[index])
                    index = playlist.find(song)
            if changed: playlist.write()
    __removed = classmethod(__removed)

    def cell_data(col, render, model, iter):
        render.set_markup(model[iter][0].format())
    cell_data = staticmethod(cell_data)

    def Menu(self, songs):
        m = gtk.Menu()
        i = qltk.MenuItem(_("_Remove from Playlist"), gtk.STOCK_REMOVE)
        m.append(i)
        return m

    __render = gtk.CellRendererText()

    def __init__(self, main):
        gtk.VBox.__init__(self, spacing=6)

        view = qltk.HintedTreeView()
        col = gtk.TreeViewColumn("Playlists", self.__render)
        col.set_cell_data_func(self.__render, Playlists.cell_data)
        view.append_column(col)
        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        swin.add(view)
        self.pack_start(swin)

        newpl = gtk.Button(stock=gtk.STOCK_NEW)
        importpl = qltk.Button(_("_Import"), gtk.STOCK_ADD)
        hb = gtk.HBox(spacing=6)
        align = gtk.Alignment(xscale=1.0)
        align.set_padding(0, 3, 6, 6)
        hb.set_homogeneous(True)
        hb.pack_start(newpl)
        hb.pack_start(importpl)
        align.add(hb)
        self.pack_start(align, expand=False)

        self.show_all()

    def restore(self):
        pass

    def reordered(self, songlist):
        pass

gobject.type_register(Playlists)

browsers = [(2, _("_Playlists"), Playlists, True)]
