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

import config
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
        if newname == self.name: return
        elif os.path.exists(os.path.join(PLAYLISTS, self.quote(newname))):
            raise ValueError(
                _("A playlist named %s already exists.") % newname)
        else:
            try: os.unlink(os.path.join(PLAYLISTS, self.quote(self.name)))
            except EnvironmentError: pass
            self.name = newname
            self.write()

    def delete(self):
        del(self[:])
        try: os.unlink(os.path.join(PLAYLISTS, self.quote(self.name)))
        except EnvironmentError: pass

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

    def playlists(klass): return [row[0] for row in self.__lists]
    playlists = classmethod(playlists)

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

        self.__view = view = qltk.HintedTreeView()
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

        view.connect('button-press-event', self.__button_press)
        view.connect('popup-menu', self.__popup_menu)
        view.get_selection().connect('changed', self.__changed)
        self.show_all()

    def __button_press(self, view, event):
        if event.button == 3:
            x, y = map(int, [event.x, event.y])
            try: path, col, cellx, celly = view.get_path_at_pos(x, y)
            except TypeError: return True
            else: view.get_selection().select_path(path)
            self.__menu(view).popup(None, None, None, event.button, event.time)
            return True

    def __popup_menu(self, view):
        self.__menu(view).popup(
            None, None, None, 0, gtk.get_current_event_time())
        return True

    def __menu(self, view):
        model, iter = view.get_selection().get_selected()
        menu = gtk.Menu()
        rem = gtk.ImageMenuItem(gtk.STOCK_REMOVE)
        def remove(model, iter):
            model[iter][0].delete()
            model.get_model().remove(
                model.convert_iter_to_child_iter(None, iter))
        rem.connect_object('activate', remove, model, iter)
        menu.append(rem)
        menu.show_all()
        menu.connect('selection-done', lambda m: m.destroy())
        return menu

    def __changed(self, selection):
        model, iter = selection.get_selected()
        if iter:
            config.set("browsers", "playlist", model[iter][0].name)
            self.emit('songs-selected', list(model[iter][0]), True)

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
        try: name = config.get("browsers", "playlist")
        except: pass
        else:
            for i, row in enumerate(self.__lists):
                if row[0].name == name:
                    self.view.get_selection().select_path((i,))
                    break

    def reordered(self, songlist):
        songs = songlist.get_songs()
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            del(model[iter][0][:])
            model[iter][0].extend(songs)
            model[iter][0].write()
            model.row_changed(model.get_path(iter), iter)

gobject.type_register(Playlists)

browsers = [(2, _("_Playlists"), Playlists, True)]
