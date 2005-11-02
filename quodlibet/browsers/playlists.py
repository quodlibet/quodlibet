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
import gobject, pango, gtk
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
        except IOError:
            if self.name: self.write()

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

    def __cmp__(self, other):
        try: return cmp(self.name, other.name)
        except AttributeError: return -1

class Playlists(gtk.VBox, Browser):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RHPaned

    def init(klass):
        model = klass.__lists.get_model()
        for playlist in os.listdir(PLAYLISTS):
            model.append(row=[Playlist(Playlist.unquote(playlist))])
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
            if changed:
                playlist.write()
                row[0] = row[0]
    __removed = classmethod(__removed)

    def cell_data(col, render, model, iter):
        render.set_property('markup', model[iter][0].format())
    cell_data = staticmethod(cell_data)

    def Menu(self, songs):
        m = gtk.Menu()
        i = qltk.MenuItem(_("_Remove from Playlist"), gtk.STOCK_REMOVE)
        m.append(i)
        return m

    __lists = gtk.TreeModelSort(gtk.ListStore(object))
    __lists.set_default_sort_func(lambda m, a, b: cmp(m[a][0], m[b][0]))

    def __init__(self, main):
        gtk.VBox.__init__(self, spacing=6)

        view = qltk.HintedTreeView()
        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        render.set_property('editable', True)
        render.connect('editing-started', self.__start_editing)
        render.connect('edited', self.__edited)
        col = gtk.TreeViewColumn("Playlists", render)
        col.set_cell_data_func(render, Playlists.cell_data)
        view.append_column(col)
        view.set_model(self.__lists)
        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        swin.add(view)
        self.pack_start(swin)

        newpl = gtk.Button(stock=gtk.STOCK_NEW)
        newpl.connect('clicked', self.__new_playlist)
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

    def __new_playlist(self, activator): 
        i = 0
        playlist = Playlist("")
        while not playlist.name:
            i += 1
            try: playlist.rename("%s %d" % (_("New Playlist"), i))
            except ValueError: pass
        self.__lists.get_model().append(row=[playlist])

    def __start_editing(self, render, editable, path):
        editable.set_text(self.__lists[path][0].name)

    def __edited(self, render, path, newname):
        try: self.__lists[path][0].rename(newname)
        except ValueError, s:
            qltk.ErrorMessage(
                widgets.main, _("Unable to rename playlist"), s).run()
        else: self.__lists[path] = self.__lists[path]

    def restore(self):
        pass

    def reordered(self, songlist):
        pass

gobject.type_register(Playlists)

browsers = [(2, _("_Playlists"), Playlists, True)]
