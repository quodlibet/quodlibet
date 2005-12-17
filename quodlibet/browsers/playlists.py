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
from tempfile import NamedTemporaryFile

import config
import const
import qltk
import util
import formats
from library import library
from browsers._base import Browser
from formats._audio import AudioFile
from qltk.views import HintedTreeView
from qltk.wlw import WaitLoadWindow

if sys.version_info < (2, 4): from sets import Set as set

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

def ParsePLS(filename, name=""):
    plname = util.fsdecode(os.path.basename(
        os.path.splitext(filename)[0])).encode('utf-8')
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
    win = WaitLoadWindow(
        None, len(files), _("Importing playlist.\n\n%d/%d songs added."),
        (0, 0))
    for i, filename in enumerate(files):
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
        if win.step(i, len(files)): break
    win.destroy()
    playlist.extend(filter(None, songs))
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

    def fromsongs(klass, songs):
        if len(songs) == 1: title = songs[0].comma("title")
        else: title = _("%(title)s and %(count)d more") % (
                {'title':songs[0].comma("title"), 'count':len(songs) - 1})
        playlist = klass.new(title)
        playlist.extend(songs)
        return playlist
    fromsongs = classmethod(fromsongs)

    def __init__(self, name):
        super(Playlist, self).__init__()
        if isinstance(name, unicode): name = name.encode('utf-8')
        self.name = name
        basename = self.quote(name)
        try:
            for line in file(os.path.join(PLAYLISTS, basename), "r"):
                line = line.rstrip()
                if line in library: self.append(library[line])
                elif library.masked(line): self.append(line)
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

    def add_songs(self, filenames):
        changed = False
        for i in range(len(self)):
            if isinstance(self[i], basestring) and self[i] in filenames:
                self[i] = library[self[i]]
                changed = True
        return changed

    def remove_songs(self, songs):
        changed = False
        for song in songs:
            if library.masked(song("~filename")):
                while True:
                    try: self[self.index(song)] = song("~filename")
                    except ValueError: break
                    else: changed = True
            else:
                while song in self: self.remove(song)
                else: changed = True
        return changed

    def delete(self):
        del(self[:])
        try: os.unlink(os.path.join(PLAYLISTS, self.quote(self.name)))
        except EnvironmentError: pass

    def write(self):
        basename = self.quote(self.name)
        f = file(os.path.join(PLAYLISTS, basename), "w")
        for song in self:
            try: f.write(song("~filename") + "\n")
            except TypeError: f.write(song + "\n")
        f.close()

    def format(self):
        return "<b>%s</b>\n<small>%s (%s)</small>" % (
            util.escape(self.name),
            ngettext("%d song", "%d songs", len(self)) % len(self),
            util.format_time(sum([t.get("~#length") for t in self
                                  if isinstance(t, AudioFile)])))

    def __cmp__(self, other):
        try: return cmp(self.name, other.name)
        except AttributeError: return -1

class Playlists(gtk.VBox, Browser):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RHPaned

    def init(klass, watcher):
        model = klass.__lists.get_model()
        for playlist in os.listdir(PLAYLISTS):
            model.append(row=[Playlist(Playlist.unquote(playlist))])
        watcher.connect('removed', klass.__removed)
        watcher.connect('added', klass.__added)
        watcher.connect('changed', klass.__changed)
    init = classmethod(init)

    def playlists(klass): return [row[0] for row in klass.__lists]
    playlists = classmethod(playlists)

    def changed(klass, playlist, refresh=True):
        model = klass.__lists
        for row in model:
            if row[0] is playlist:
                if refresh:
                    klass.__lists.row_changed(row.path, row.iter)
                playlist.write()
                break
        else:
            model.get_model().append(row=[playlist])
            playlist.write()
    changed = classmethod(changed)

    def __removed(klass, watcher, songs):
        for playlist in klass.playlists():
            if playlist.remove_songs(songs): Playlists.changed(playlist)
    __removed = classmethod(__removed)

    def __added(klass, watcher, songs):
        filenames = set([song("~filename") for song in songs])
        for playlist in klass.playlists():
            if playlist.add_songs(filenames): Playlists.changed(playlist)
    __added = classmethod(__added)

    def __changed(klass, watcher, songs):
        for playlist in klass.playlists():
            for song in songs:
                if song in playlist:
                    Playlists.changed(playlist, refresh=False)
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

    def __init__(self, watcher, player):
        gtk.VBox.__init__(self, spacing=6)
        self.__main = bool(player)
        self.__view = view = HintedTreeView()
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
        importpl.connect('clicked', self.__import, watcher)
        hb = gtk.HBox(spacing=6)
        hb.set_homogeneous(True)
        hb.pack_start(newpl)
        hb.pack_start(importpl)
        self.pack_start(hb, expand=False)

        view.connect('popup-menu', self.__popup_menu)

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 0),
                   ("text/uri-list", 0, 1),
                   ("text/x-moz-url", 0, 2)]
        view.drag_dest_set(gtk.DEST_DEFAULT_ALL, targets,
                           gtk.gdk.ACTION_COPY|gtk.gdk.ACTION_DEFAULT)
        view.connect('drag-data-received', self.__drag_data_received, watcher)
        view.connect('drag-motion', self.__drag_motion)
        view.connect('drag-leave', self.__drag_leave)
        if player: view.connect('row-activated', self.__play, player)
        else: render.set_property('editable', True)
        view.get_selection().connect('changed', self.activate)

        s = view.get_model().connect('row-changed', self.__check_current)
        self.connect_object('destroy', view.get_model().disconnect, s)

        self.show_all()

    def __play(self, view, path, column, player):
        player.reset()
        player.next()

    def __check_current(self, model, path, iter):
        model, citer = self.__view.get_selection().get_selected()
        if citer and model.get_path(citer) == path: self.activate()

    def __drag_motion(self, view, ctx, x, y, time):
        if "text/x-quodlibet-songs" in ctx.targets:
            try: path = view.get_dest_row_at_pos(x, y)[0]
            except TypeError:
                path = (len(view.get_model()) - 1,)
                pos = gtk.TREE_VIEW_DROP_AFTER
            else: pos = gtk.TREE_VIEW_DROP_INTO_OR_AFTER
            if path > (-1,): view.set_drag_dest_row(path, pos)
            return True
        else:
            # Highlighting the view itself doesn't work.
            view.parent.drag_highlight()
            return True

    def __drag_leave(self, view, ctx, time):
        view.parent.drag_unhighlight()

    def __remove(self, iters, smodel):
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            map(smodel.remove, iters)
            playlist = model[iter][0]            
            del(playlist[:])
            for row in smodel: playlist.append(row[0])
            Playlists.changed(playlist)
            self.activate()

    def __drag_data_received(self, view, ctx, x, y, sel, tid, etime, watcher):
        # TreeModelSort doesn't support GtkTreeDragDestDrop.
        view.emit_stop_by_name('drag-data-received')
        model = view.get_model()
        if tid == 0:
            filenames = sel.data.split("\x00")
            songs = filter(None, map(library.get, filenames))
            if not songs: return True
            try: path, pos = view.get_dest_row_at_pos(x, y)
            except TypeError:
                playlist = Playlist.fromsongs(songs)
                gobject.idle_add(self.__select_playlist, playlist)
            else:
                playlist = model[path][0]
                playlist.extend(songs)
            Playlists.changed(playlist)
            ctx.finish(True, False, etime)
        else:
            if tid == 1:
                uri = sel.get_uris()[0]
                name = os.path.basename(uri)
            elif tid == 2:
                uri, name = sel.data.decode('ucs-2', 'replace').split('\n')
            else:
                ctx.finish(False, False, etime)
                return
            name = name or os.path.basename(uri) or _("New Playlist")
            uri = uri.encode('utf-8')
            sock = urllib.urlopen(uri)
            f = NamedTemporaryFile()
            f.write(sock.read()); f.flush()
            if uri.lower().endswith('.pls'): playlist = ParsePLS(f.name)
            elif uri.lower().endswith('.m3u'): playlist = ParseM3U(f.name)
            else: playlist = None
            if playlist:
                watcher.added(filter(library.add_song, playlist))
                if name: playlist.rename(name)
                Playlists.changed(playlist)
                ctx.finish(True, False, etime)
            else:
                ctx.finish(False, False, etime)
                qltk.ErrorMessage(
                    qltk.get_top_parent(self),
                    _("Unable to import playlist"),
                    _("Quod Libet can only import playlists in the M3U "
                      "and PLS formats.")).run()

    def __select_playlist(self, playlist):
        view = self.__view
        model = view.get_model()
        for row in model:
            if row[0] is playlist:
                view.get_selection().select_iter(row.iter)

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
        songs = filter(lambda s: isinstance(s, AudioFile), songs)
        name = iter and model[iter][0].name or ""
        if self.__main: config.set("browsers", "playlist", name)
        self.emit('songs-selected', songs, True)

    def __new_playlist(self, activator):
        playlist = Playlist.new()
        self.__lists.get_model().append(row=[playlist])
        self.__select_playlist(playlist)

    def __start_editing(self, render, editable, path):
        editable.set_text(self.__lists[path][0].name)

    def __edited(self, render, path, newname):
        try: self.__lists[path][0].rename(newname)
        except ValueError, s:
            qltk.ErrorMessage(
                None, _("Unable to rename playlist"), s).run()
        else: self.__lists[path] = self.__lists[path]
        render.set_property('editable', not self.__main)

    def __import(self, activator, watcher):
        filt = lambda fn: fn.endswith(".pls") or fn.endswith(".m3u")
        from qltk.chooser import FileChooser
        chooser = FileChooser(
            self, _("Import Playlist"), filt, os.getenv("HOME"))
        files = chooser.run()
        chooser.destroy()
        for filename in files:
            if filename.endswith(".m3u"):
                playlist = ParseM3U(filename)
            elif filename.endswith(".pls"):
                playlist = ParsePLS(filename)
            else:
                qltk.ErrorMessage(
                    qltk.get_top_parent(self),
                    _("Unable to import playlist"),
                    _("Quod Libet can only import playlists in the M3U "
                      "and PLS formats.")).run()
                return
            Playlists.changed(playlist)
            watcher.added(filter(library.add_song, playlist))

    def restore(self):
        try: name = config.get("browsers", "playlist")
        except: pass
        else:
            for i, row in enumerate(self.__lists):
                if row[0].name == name:
                    self.__view.get_selection().select_path((i,))
                    break

    def reordered(self, songlist):
        songs = songlist.get_songs()
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            playlist = model[iter][0]
            playlist[:] = songs
        else:
            playlist = Playlist.fromsongs(songs)
            gobject.idle_add(self.__select_playlist, playlist)
        Playlists.changed(playlist)

gobject.type_register(Playlists)

browsers = [(2, _("_Playlists"), Playlists, True)]
