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

import config
import player
import const
import qltk
import util
import formats
from library import library
from browsers.base import Browser

from widgets import FileChooser
from widgets import widgets

PLAYLISTS = os.path.join(const.DIR, "playlists")
if not os.path.isdir(PLAYLISTS): util.mkdir(PLAYLISTS)

def ParseM3U(filename):
    plname = util.fsdecode(os.path.basename(
        os.path.splitext(filename)[0])).encode('utf-8')
    filenames = []
    for line in file(filename):
        line = line.strip()
        if line.startswith("#"): continue
        else: filenames.append(line)
    return __ParsePlaylist(plname, filename, filenames)

def ParsePLS(filename):
    plname = util.fsdecode(os.path.basename(filename)).encode('utf-8')
    filenames = []
    for line in file(filename):
        line = line.strip()
        if not line.lower().startswith("file"): continue
        else:
            try: line = line[line.index("=")+1:].strip()
            except ValueError: pass
            else: filenames.append(line)
    return __ParsePlaylist(plname, filename, filenames)

def __ParsePlaylist(name, plfilename, files):
    playlist = Playlist.new(name)
    songs = []
    for filename in files:
        type, path = urllib.splittype(filename)
        if type is None:
            # Plain filename.
            filename = os.path.realpath(os.path.join(
                os.path.dirname(plfilename), filename))
            if filename in library: songs.append(library[filename])
            else: songs.append(formats.MusicFile(filename))
        elif type == "file":
            # URI-encoded local filename.
            filename = os.path.realpath(os.path.join(
                os.path.dirname(plfilename), urllib.url2pathname(path)))
            if filename in library: songs.append(library[filename])
            else: songs.append(formats.MusicFile(filename))
        else:
            # Who knows! Hand it off to GStreamer.
            songs.append(formats.remote.RemoteFile(filename))
    playlist.extend(filter(None, songs))
    widgets.watcher.added(filter(library.add_song, playlist))
    return playlist

class Playlist(list):
    quote = staticmethod(lambda text: urllib.quote(text, safe=""))    
    unquote = staticmethod(urllib.unquote)

    def new(klass, base=_("New Playlist")):
        p = Playlist("")
        i = 0
        try: p.rename(base)
        except ValueError:
            while not p.name:
                i += 1
                try: p.rename("%s %d" % (base, i))
                except ValueError: pass
        return p
    new = classmethod(new)

    def __init__(self, name):
        super(Playlist, self).__init__()
        if isinstance(name, unicode): name = name.encode('utf-8')
        self.name = name
        basename = self.quote(name)
        try:
            for line in file(os.path.join(PLAYLISTS, basename), "r"):
                line = line.rstrip()
                if line in library: self.append(library[line])
        except IOError:
            if self.name: self.write()

    def rename(self, newname):
        if isinstance(newname, unicode): newname = newname.encode('utf-8')
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
        for song in self: f.write(song("~filename") + "\n")
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
        widgets.watcher.connect('changed', klass.__changed)
    init = classmethod(init)

    def playlists(klass): return [row[0] for row in klass.__lists]
    playlists = classmethod(playlists)

    def changed(klass, playlist):
        model = klass.__lists
        for i, row in enumerate(model):
            if row[0] is playlist:
                path = (i,)
                klass.__lists.row_changed(path, model.get_iter(path))
                playlist.write()
                break
        else:
            model.get_model().append(row=[playlist])
            playlist.write()
    changed = classmethod(changed)

    def __removed(klass, watcher, songs):
        for row in klass.__lists:
            playlist = row[0]
            changed = False
            for song in songs:
                try:
                    while True:
                        playlist.remove(song)
                        changed = True
                except ValueError: pass
            if changed: Playlists.changed(playlist)
    __removed = classmethod(__removed)

    def __changed(klass, watcher, songs):
        for row in klass.__lists:
            playlist = row[0]
            for song in songs:
                if song in playlist:
                    Playlists.changed(playlist)
                    break
    __changed = classmethod(__changed)

    def cell_data(col, render, model, iter):
        render.markup = model[iter][0].format()
        render.set_property('markup', render.markup)
    cell_data = staticmethod(cell_data)

    def Menu(self, songs, songlist):
        model, rows = songlist.get_selection().get_selected_rows()
        iters = map(model.get_iter, rows)
        m = gtk.Menu()
        i = qltk.MenuItem(_("_Remove from Playlist"), gtk.STOCK_REMOVE)
        i.connect_object('activate', self.__remove, iters, model)
        i.set_sensitive(bool(self.__view.get_selection().get_selected()[1]))
        m.append(i)
        return m

    __lists = gtk.TreeModelSort(gtk.ListStore(object))
    __lists.set_default_sort_func(lambda m, a, b: cmp(m[a][0], m[b][0]))

    def __init__(self, main):
        gtk.VBox.__init__(self, spacing=6)
        self.__main = main
        self.__view = view = qltk.HintedTreeView()
        self.__render = render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        render.connect('editing-started', self.__start_editing)
        render.connect('edited', self.__edited)
        col = gtk.TreeViewColumn("Playlists", render)
        col.set_cell_data_func(render, Playlists.cell_data)
        view.append_column(col)
        view.set_model(self.__lists)
        view.set_rules_hint(True)
        view.set_headers_visible(False)
        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        swin.add(view)
        self.pack_start(swin)

        newpl = gtk.Button(stock=gtk.STOCK_NEW)
        newpl.connect('clicked', self.__new_playlist)
        importpl = qltk.Button(_("_Import"), gtk.STOCK_ADD)
        importpl.connect('clicked', self.__import)
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

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 1)]
        view.drag_dest_set(gtk.DEST_DEFAULT_ALL, targets, gtk.gdk.ACTION_COPY)
        view.connect('drag-data-received', self.__drag_data_received)
        view.connect('drag-motion', self.__drag_motion)
        if main: view.connect('row-activated', self.__play)
        else: render.set_property('editable', True)
        view.get_selection().connect('changed', self.activate)

        s = view.get_model().connect('row-changed', self.__check_current)
        self.connect_object('destroy', view.get_model().disconnect, s)

        self.show_all()

    def __play(self, *args):
        player.playlist.reset()
        player.playlist.next()

    def __check_current(self, model, path, iter):
        model, citer = self.__view.get_selection().get_selected()
        if citer and model.get_path(citer) == path: self.activate()

    def __drag_motion(self, view, ctx, x, y, time):
        try: path = view.get_dest_row_at_pos(x, y)[0]
        except TypeError:
            path = (len(view.get_model()) - 1,)
            pos = gtk.TREE_VIEW_DROP_AFTER
        else: pos = gtk.TREE_VIEW_DROP_INTO_OR_AFTER
        if path > (-1,): view.set_drag_dest_row(path, pos)
        return True

    def __remove(self, iters, smodel):
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            map(smodel.remove, iters)
            playlist = model[iter][0]            
            del(playlist[:])
            for row in smodel: playlist.append(row[0])
            Playlists.changed(playlist)
            self.activate()

    def __drag_data_received(self, view, ctx, x, y, sel, info, etime):
        # TreeModelSort doesn't support GtkTreeDragDestDrop.
        view.emit_stop_by_name('drag-data-received')
        model = view.get_model()
        filenames = sel.data.split("\x00")
        songs = filter(None, map(library.get, filenames))
        if not songs: return True
        try: path, pos = view.get_dest_row_at_pos(x, y)
        except TypeError:
            if len(songs) == 1: title = songs[0].comma("title")
            else: title = _("%(title)s and %(count)d more") % (
                    {'title':songs[0].comma("title"), 'count':len(songs) - 1})
            playlist = Playlist.new(title)
            iter = model.get_model().append(row=[playlist])
            iter = model.convert_child_iter_to_iter(None, iter)
        else:
            playlist = model[path][0]
            iter = model.get_iter(path)
        playlist.extend(songs)
        Playlists.changed(playlist)
        ctx.finish(True, True, etime)
        return True

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
        ren = qltk.MenuItem(_("_Rename"), gtk.STOCK_EDIT)
        def rename(path):
            self.__render.set_property('editable', True)
            view.set_cursor(path, view.get_columns()[0], start_editing=True)
        ren.connect_object('activate', rename, model.get_path(iter))
        menu.append(ren)

        rem = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        def remove(model, iter):
            model[iter][0].delete()
            model.get_model().remove(
                model.convert_iter_to_child_iter(None, iter))
        rem.connect_object('activate', remove, model, iter)
        menu.append(rem)
        menu.show_all()
        menu.connect('selection-done', lambda m: m.destroy())
        return menu

    def activate(self, *args):
        model, iter = self.__view.get_selection().get_selected()
        songs = iter and list(model[iter][0]) or []
        name = iter and model[iter][0].name or ""
        if self.__main:
            config.set("browsers", "playlist", name)
        self.emit('songs-selected', songs, True)

    def __new_playlist(self, activator):
        self.__lists.get_model().append(row=[Playlist.new()])

    def __start_editing(self, render, editable, path):
        editable.set_text(self.__lists[path][0].name)

    def __edited(self, render, path, newname):
        try: self.__lists[path][0].rename(newname)
        except ValueError, s:
            qltk.ErrorMessage(
                widgets.main, _("Unable to rename playlist"), s).run()
        else: self.__lists[path] = self.__lists[path]
        render.set_property('editable', not self.__main)

    def __import(self, activator):
        filt = lambda fn: fn.endswith(".pls") or fn.endswith(".m3u")
        chooser = FileChooser(
            widgets.main, _("Import Playlist"), filt, os.getenv("HOME"))
        files = chooser.run()
        chooser.destroy()
        for filename in files:
            if filename.endswith(".m3u"):
                Playlists.changed(ParseM3U(filename))
            elif filename.endswith(".pls"):
                Playlists.changed(ParsePLS(filename))

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
            playlist = model[iter][0]
            playlist[:] = songs
            Playlists.changed(playlist)

gobject.type_register(Playlists)

browsers = [(2, _("_Playlists"), Playlists, True)]
