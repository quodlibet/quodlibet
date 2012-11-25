# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#           2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import urllib

import gobject
import gtk
import pango

from quodlibet import config
from quodlibet import const
from quodlibet import formats
from quodlibet import qltk
from quodlibet import util

from tempfile import NamedTemporaryFile

from quodlibet.browsers._base import Browser
from quodlibet.formats._audio import AudioFile
from quodlibet.util.collection import Playlist
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.qltk.wlw import WaitLoadWindow
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.x import ScrolledWindow, Alignment
from quodlibet.util.uri import URI
from quodlibet.util.dprint import print_d

PLAYLISTS = os.path.join(const.USERDIR, "playlists")
if not os.path.isdir(PLAYLISTS): util.mkdir(PLAYLISTS)

def ParseM3U(filename, library=None):
    plname = util.fsdecode(os.path.basename(
        os.path.splitext(filename)[0])).encode('utf-8')
    filenames = []
    for line in file(filename):
        line = line.strip()
        if line.startswith("#"): continue
        else: filenames.append(line)
    return __ParsePlaylist(plname, filename, filenames, library)

def ParsePLS(filename, name="", library=None):
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
    return __ParsePlaylist(plname, filename, filenames, library)

def __ParsePlaylist(name, plfilename, files, library):
    playlist = Playlist.new(PLAYLISTS, name, library=library)
    songs = []
    win = WaitLoadWindow(
        None, len(files),
        _("Importing playlist.\n\n%(current)d/%(total)d songs added."))
    for i, filename in enumerate(files):
        try: uri = URI(filename)
        except ValueError:
            # Plain filename.
            filename = os.path.realpath(os.path.join(
                os.path.dirname(plfilename), filename))
            if library and filename in library:
                songs.append(library[filename])
            else:
                songs.append(formats.MusicFile(filename))
        else:
            if uri.scheme == "file":
                # URI-encoded local filename.
                filename = os.path.realpath(os.path.join(
                    os.path.dirname(plfilename), uri.filename))
                if library and filename in library:
                    songs.append(library[filename])
                else:
                    songs.append(formats.MusicFile(filename))
            else:
                # Who knows! Hand it off to GStreamer.
                songs.append(formats.remote.RemoteFile(uri))
        if win.step(): break
    win.destroy()
    playlist.extend(filter(None, songs))
    return playlist


class ConfirmRemovePlaylistDialog(qltk.Message):
    def __init__(self, parent, playlist):
        title = (_("Are you sure you want to delete the playlist '%s'?")
                 % playlist.name)
        description = (_("All information about the selected playlist "
                         "will be deleted and can not be restored."))

        super(ConfirmRemovePlaylistDialog, self).__init__(
            gtk.MESSAGE_WARNING, parent, title, description, gtk.BUTTONS_NONE)

        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_DELETE, gtk.RESPONSE_YES)


class ConfirmRemoveDuplicatesDialog(qltk.Message):
    def __init__(self, parent, playlist, count):
        title = ngettext("Are you sure you want to remove %d duplicate song?",
                         "Are you sure you want to remove %d duplicate songs?",
                         count) % count
        description = (_("The duplicate songs will be removed "
                         "from the playlist '%s'.") % playlist.name)

        super(ConfirmRemoveDuplicatesDialog, self).__init__(
            gtk.MESSAGE_WARNING, parent, title, description, gtk.BUTTONS_NONE)

        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_DELETE, gtk.RESPONSE_YES)


class GetPlaylistName(GetStringDialog):
    def __init__(self, parent):
        super(GetPlaylistName, self).__init__(
            parent, _("New Playlist"),
            _("Enter a name for the new playlist:"),
            okbutton=gtk.STOCK_ADD)

class Menu(gtk.Menu):
    def __init__(self, songs, parent=None):
        super(Menu, self).__init__()
        i = gtk.MenuItem(_("_New Playlist"))
        i.connect_object('activate',
            self.__add_to_playlist, None, songs, parent)
        self.append(i)
        self.append(gtk.SeparatorMenuItem())
        self.set_size_request(int(i.size_request()[0] * 2), -1)

        for playlist in Playlists.playlists():
            name = playlist.name
            i = gtk.CheckMenuItem(name)
            some, all = playlist.has_songs(songs)
            i.set_active(some)
            i.set_inconsistent(some and not all)
            i.child.set_ellipsize(pango.ELLIPSIZE_END)
            i.connect_object(
                'activate', self.__add_to_playlist, playlist, songs, parent)
            self.append(i)

    def __add_to_playlist(playlist, songs, parent):
        if playlist is None:
            if len(songs) == 1:
                title = songs[0].comma("title")
            else:
                title = ngettext(
                    "%(title)s and %(count)d more",
                    "%(title)s and %(count)d more",
                    len(songs) - 1) % (
                    {'title': songs[0].comma("title"), 'count': len(songs) - 1})
            title = GetPlaylistName(qltk.get_top_parent(parent)).run(title)
            if title is None: return
            playlist = Playlist.new(PLAYLISTS, title)
        playlist.extend(songs)
        Playlists.changed(playlist)
    __add_to_playlist = staticmethod(__add_to_playlist)

class Playlists(gtk.VBox, Browser):
    __gsignals__ = Browser.__gsignals__
    expand = qltk.RHPaned

    name = _("Playlists")
    accelerated_name = _("_Playlists")
    priority = 2
    replaygain_profiles = ["track"]

    @classmethod
    def init(klass, library):
        model = klass.__lists.get_model()
        for playlist in os.listdir(util.fsnative(PLAYLISTS)):
            try:
                playlist = Playlist(PLAYLISTS, Playlist.unquote(playlist),
                                    library=library)
                model.append(row=[playlist])
            except EnvironmentError:
                pass
        library.connect('removed', klass.__removed)
        library.connect('added', klass.__added)
        library.connect('changed', klass.__changed)

    @classmethod
    def playlists(klass):
        return [row[0] for row in klass.__lists]

    @classmethod
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

    @classmethod
    def __removed(klass, library, songs):
        for playlist in klass.playlists():
            if playlist.remove_songs(songs, library):
                Playlists.changed(playlist)

    @classmethod
    def __added(klass, library, songs):
        filenames = set([song("~filename") for song in songs])
        for playlist in klass.playlists():
            if playlist.add_songs(filenames, library):
                Playlists.changed(playlist)

    @classmethod
    def __changed(klass, library, songs):
        for playlist in klass.playlists():
            for song in songs:
                if song in playlist.songs:
                    Playlists.changed(playlist, refresh=False)
                    break

    @staticmethod
    def cell_data(col, render, model, iter):
        render.markup = model[iter][0].format()
        render.set_property('markup', render.markup)

    def Menu(self, songs, songlist, library):
        menu = super(Playlists, self).Menu(songs, songlist, library)
        model, rows = songlist.get_selection().get_selected_rows()
        iters = map(model.get_iter, rows)
        i = qltk.MenuItem(_("_Remove from Playlist"), gtk.STOCK_REMOVE)
        i.connect_object('activate', self.__remove, iters, model)
        i.set_sensitive(bool(self.__view.get_selection().get_selected()[1]))
        menu.preseparate()
        menu.prepend(i)
        return menu

    __lists = gtk.TreeModelSort(gtk.ListStore(object))
    __lists.set_default_sort_func(lambda m, a, b: cmp(m[a][0], m[b][0]))

    def __init__(self, library, main):
        super(Playlists, self).__init__(spacing=6)
        self.__main = main
        self.__view = view = RCMHintedTreeView()
        self.__view.set_enable_search(True)
        self.__view.set_search_column(0)
        self.__view.set_search_equal_func(
            lambda model, col, key, iter:
            not model[iter][col].name.lower().startswith(key.lower()))
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
        swin = ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        swin.add(view)
        self.pack_start(swin)

        newpl = gtk.Button(stock=gtk.STOCK_NEW)
        newpl.connect('clicked', self.__new_playlist)
        importpl = qltk.Button(_("_Import"), gtk.STOCK_ADD)
        importpl.connect('clicked', self.__import, library)
        hb = gtk.HBox(spacing=6)
        hb.set_homogeneous(True)
        hb.pack_start(newpl)
        hb.pack_start(importpl)
        self.pack_start(Alignment(hb, left=3, bottom=3), expand=False)

        view.connect('popup-menu', self.__popup_menu, library)

        targets = [("text/x-quodlibet-songs", gtk.TARGET_SAME_APP, 0),
                   ("text/uri-list", 0, 1),
                   ("text/x-moz-url", 0, 2)]
        view.drag_dest_set(gtk.DEST_DEFAULT_ALL, targets,
                           gtk.gdk.ACTION_COPY|gtk.gdk.ACTION_DEFAULT)
        view.drag_source_set(gtk.gdk.BUTTON1_MASK, targets[:2],
                             gtk.gdk.ACTION_COPY)
        view.connect('drag-data-received', self.__drag_data_received, library)
        view.connect('drag-data-get', self.__drag_data_get)
        view.connect('drag-motion', self.__drag_motion)
        view.connect('drag-leave', self.__drag_leave)
        if main:
            view.connect('row-activated', lambda *x: self.emit("activated"))
        else:
            render.set_property('editable', True)
        view.get_selection().connect('changed', self.activate)

        s = view.get_model().connect('row-changed', self.__check_current)
        self.connect_object('destroy', view.get_model().disconnect, s)

        self.accelerators = gtk.AccelGroup()
        keyval, mod = gtk.accelerator_parse("F2")
        self.accelerators.connect_group(keyval, mod, 0, self.__rename)

        self.connect('key-press-event', self.__key_pressed)

        self.show_all()

    def __key_pressed(self, widget, event):
        if qltk.is_accel(event, "Delete"):
            model, iter = self.__view.get_selection().get_selected()
            if not iter:
                return False

            playlist = model[iter][0]
            dialog = ConfirmRemovePlaylistDialog(self, playlist)
            if dialog.run() == gtk.RESPONSE_YES:
                playlist.delete()
                model.get_model().remove(
                    model.convert_iter_to_child_iter(None, iter))

        return False

    def __rename(self, group, acceleratable, keyval, modifier):
        model, iter = self.__view.get_selection().get_selected()
        if iter:
            self.__render.set_property('editable', True)
            self.__view.set_cursor(model.get_path(iter),
                                   self.__view.get_columns()[0],
                                   start_editing=True)

    def __check_current(self, model, path, iter):
        model, citer = self.__view.get_selection().get_selected()
        if citer and model.get_path(citer) == path:
            songlist = qltk.get_top_parent(self).songlist
            self.activate(resort=not songlist.is_sorted())

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
            playlist.clear()
            playlist.extend([row[0] for row in smodel])
            Playlists.changed(playlist)
            self.activate()

    def __drag_data_received(self, view, ctx, x, y, sel, tid, etime, library):
        # TreeModelSort doesn't support GtkTreeDragDestDrop.
        view.emit_stop_by_name('drag-data-received')
        model = view.get_model()
        if tid == 0:
            filenames = sel.data.split("\x00")
            songs = filter(None, map(library.get, filenames))
            if not songs: return True
            try: path, pos = view.get_dest_row_at_pos(x, y)
            except TypeError:
                playlist = Playlist.fromsongs(PLAYLISTS, songs, library)
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
                uri, name = sel.data.decode('utf16', 'replace').split('\n')
            else:
                ctx.finish(False, False, etime)
                return
            name = name or os.path.basename(uri) or _("New Playlist")
            uri = uri.encode('utf-8')
            try:
                sock = urllib.urlopen(uri)
                f = NamedTemporaryFile()
                f.write(sock.read()); f.flush()
                if uri.lower().endswith('.pls'):
                    playlist = ParsePLS(f.name, library=library)
                elif uri.lower().endswith('.m3u'):
                    playlist = ParseM3U(f.name, library=library)
                else:
                    raise IOError
                library.add_filename(playlist)
                if name: playlist.rename(name)
                Playlists.changed(playlist)
                ctx.finish(True, False, etime)
            except IOError:
                ctx.finish(False, False, etime)
                qltk.ErrorMessage(
                    qltk.get_top_parent(self),
                    _("Unable to import playlist"),
                    _("Quod Libet can only import playlists in the M3U "
                      "and PLS formats.")).run()

    def __drag_data_get(self, view, ctx, sel, tid, etime):
        model, iters = self.__view.get_selection().get_selected_rows()
        songs = []
        for iter in filter(lambda i: i, iters):
            songs += list(model[iter][0])
        if tid == 0:
            filenames = [song("~filename") for song in songs]
            sel.set("text/x-quodlibet-songs", 8, "\x00".join(filenames))
        else:
            sel.set_uris([song("~uri") for song in songs])

    def __select_playlist(self, playlist):
        view = self.__view
        model = view.get_model()
        for row in model:
            if row[0] is playlist:
                view.get_selection().select_iter(row.iter)

    def __popup_menu(self, view, library):
        # TODO: Consider allowing plugins to expose themselves in playlist
        model, itr = view.get_selection().get_selected()
        if itr is None:
            return
        songs = list(model[itr][0])
        songs = filter(lambda s: isinstance(s, AudioFile), songs)
        menu = SongsMenu(
            library, songs, playlists=False, remove=False, parent=self)
        menu.preseparate()

        def _de_duplicate(model, itr):
            playlist = model[itr][0]
            unique = set()
            dupes = list()
            for s in songs:
                if s in unique: dupes.append(s)
                else: unique.add(s)
            if len(dupes) < 1:
                print_d("No duplicates in this playlist")
                return
            dialog = ConfirmRemoveDuplicatesDialog(self, playlist, len(dupes))
            if dialog.run() == gtk.RESPONSE_YES:
                playlist.remove_songs(dupes, library, True)
                Playlists.changed(playlist)
                self.activate()

        de_dupe = gtk.MenuItem(_("Remove Duplicates"))
        de_dupe.connect_object('activate', _de_duplicate, model, itr)
        de_dupe.set_sensitive(not model[itr][0].has_duplicates())
        menu.prepend(de_dupe)

        def _shuffle(model, itr):
            playlist = model[itr][0]
            playlist.shuffle()
            self.activate()

        shuffle = gtk.MenuItem(_("_Shuffle"))
        shuffle .connect_object('activate', _shuffle, model, itr)
        shuffle.set_sensitive(bool(len(model[itr][0])))
        menu.prepend(shuffle)
        menu.prepend(gtk.SeparatorMenuItem())

        def _remove(model, itr):
            playlist = model[itr][0]
            dialog = ConfirmRemovePlaylistDialog(self, playlist)
            if dialog.run() == gtk.RESPONSE_YES:
                playlist.delete()
                model.get_model().remove(
                    model.convert_iter_to_child_iter(None, itr))

        rem = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        rem.connect_object('activate', _remove, model, itr)
        menu.prepend(rem)

        def _rename(path):
            self.__render.set_property('editable', True)
            view.set_cursor(path, view.get_columns()[0], start_editing=True)

        ren = qltk.MenuItem(_("_Rename"), gtk.STOCK_EDIT)
        keyval, mod = gtk.accelerator_parse("F2")
        ren.add_accelerator(
            'activate', self.accelerators, keyval, mod, gtk.ACCEL_VISIBLE)
        ren.connect_object('activate', _rename, model.get_path(itr))
        menu.prepend(ren)

        menu.show_all()
        return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def activate(self, widget=None, resort=True):
        model, iter = self.__view.get_selection().get_selected()
        songs = iter and list(model[iter][0]) or []
        songs = filter(lambda s: isinstance(s, AudioFile), songs)
        self.emit('songs-selected', songs, resort)

    def save(self):
        model, iter = self.__view.get_selection().get_selected()
        name = iter and model[iter][0].name or ""
        config.set("browsers", "playlist", name)

    def __new_playlist(self, activator):
        playlist = Playlist.new(PLAYLISTS)
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

    def __import(self, activator, library):
        filt = lambda fn: fn.endswith(".pls") or fn.endswith(".m3u")
        from quodlibet.qltk.chooser import FileChooser
        chooser = FileChooser(self, _("Import Playlist"), filt, const.HOME)
        files = chooser.run()
        chooser.destroy()
        for filename in files:
            if filename.endswith(".m3u"):
                playlist = ParseM3U(filename, library=library)
            elif filename.endswith(".pls"):
                playlist = ParsePLS(filename, library=library)
            else:
                qltk.ErrorMessage(
                    qltk.get_top_parent(self),
                    _("Unable to import playlist"),
                    _("Quod Libet can only import playlists in the M3U "
                      "and PLS formats.")).run()
                return
            Playlists.changed(playlist)
            library.add(playlist)

    def restore(self):
        try:
            name = config.get("browsers", "playlist")
        except Exception: return
        self.__view.select_by_func(lambda r: r[0].name == name, one=True)

    def reordered(self, songlist):
        songs = songlist.get_songs()
        model, iter = self.__view.get_selection().get_selected()
        playlist = None
        if iter:
            playlist = model[iter][0]
            playlist[:] = songs
        elif songs:
            playlist = Playlist.fromsongs(PLAYLISTS, songs)
            gobject.idle_add(self.__select_playlist, playlist)
        if playlist:
            Playlists.changed(playlist, refresh=False)

browsers = [Playlists]
