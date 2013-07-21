# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#           2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import urllib

from gi.repository import Gtk, GLib, Pango, Gdk

from quodlibet import config, mkdir
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
from quodlibet.qltk.x import ScrolledWindow, Alignment, SeparatorMenuItem
from quodlibet.util.path import fsdecode
from quodlibet.util.uri import URI
from quodlibet.util.dprint import print_d


PLAYLISTS = os.path.join(const.USERDIR, "playlists")
if not os.path.isdir(PLAYLISTS):
    mkdir(PLAYLISTS)


def ParseM3U(filename, library=None):
    plname = fsdecode(os.path.basename(
        os.path.splitext(filename)[0])).encode('utf-8')
    filenames = []
    for line in file(filename):
        line = line.strip()
        if line.startswith("#"):
            continue
        else:
            filenames.append(line)
    return __ParsePlaylist(plname, filename, filenames, library)


def ParsePLS(filename, name="", library=None):
    plname = fsdecode(os.path.basename(
        os.path.splitext(filename)[0])).encode('utf-8')
    filenames = []
    for line in file(filename):
        line = line.strip()
        if not line.lower().startswith("file"):
            continue
        else:
            try:
                line = line[line.index("=") + 1:].strip()
            except ValueError:
                pass
            else:
                filenames.append(line)
    return __ParsePlaylist(plname, filename, filenames, library)


def __ParsePlaylist(name, plfilename, files, library):
    playlist = Playlist.new(PLAYLISTS, name, library=library)
    songs = []
    win = WaitLoadWindow(
        None, len(files),
        _("Importing playlist.\n\n%(current)d/%(total)d songs added."))
    win.show()
    for i, filename in enumerate(files):
        try:
            uri = URI(filename)
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
        if win.step():
            break
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
            Gtk.MessageType.WARNING, parent, title, description,
            Gtk.ButtonsType.NONE)

        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_DELETE, Gtk.ResponseType.YES)


class ConfirmRemoveDuplicatesDialog(qltk.Message):
    def __init__(self, parent, playlist, count):
        title = ngettext("Are you sure you want to remove %d duplicate song?",
                         "Are you sure you want to remove %d duplicate songs?",
                         count) % count
        description = (_("The duplicate songs will be removed "
                         "from the playlist '%s'.") % playlist.name)

        super(ConfirmRemoveDuplicatesDialog, self).__init__(
            Gtk.MessageType.WARNING, parent, title, description,
            Gtk.ButtonsType.NONE)

        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_DELETE, Gtk.ResponseType.YES)


class GetPlaylistName(GetStringDialog):
    def __init__(self, parent):
        super(GetPlaylistName, self).__init__(
            parent, _("New Playlist"),
            _("Enter a name for the new playlist:"),
            okbutton=Gtk.STOCK_ADD)


class Menu(Gtk.Menu):
    def __init__(self, songs, parent=None):
        super(Menu, self).__init__()
        i = Gtk.MenuItem(_("_New Playlist"), use_underline=True)
        i.connect_object(
            'activate', self.__add_to_playlist, None, songs, parent)
        self.append(i)
        self.append(SeparatorMenuItem())
        self.set_size_request(int(i.size_request().width * 2), -1)

        for playlist in Playlists.playlists():
            name = playlist.name
            i = Gtk.CheckMenuItem(name)
            some, all = playlist.has_songs(songs)
            i.set_active(some)
            i.set_inconsistent(some and not all)
            i.get_child().set_ellipsize(Pango.EllipsizeMode.END)
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
                    len(songs) - 1) % {
                        'title': songs[0].comma("title"),
                        'count': len(songs) - 1
                    }
            title = GetPlaylistName(qltk.get_top_parent(parent)).run(title)
            if title is None:
                return
            playlist = Playlist.new(PLAYLISTS, title)
        playlist.extend(songs)
        Playlists.changed(playlist)
    __add_to_playlist = staticmethod(__add_to_playlist)


DND_QL, DND_URI_LIST, DND_MOZ_URL = range(3)


class Playlists(Gtk.VBox, Browser):
    __gsignals__ = Browser.__gsignals__

    name = _("Playlists")
    accelerated_name = _("_Playlists")
    priority = 2
    replaygain_profiles = ["track"]

    def pack(self, songpane):
        container = qltk.RHPaned()
        self.show()
        container.pack1(self, True, False)
        container.pack2(songpane, True, False)
        return container

    def unpack(self, container, songpane):
        container.remove(songpane)
        container.remove(self)

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
    def cell_data(col, render, model, iter, data):
        render.markup = model[iter][0].format()
        render.set_property('markup', render.markup)

    def Menu(self, songs, songlist, library):
        menu = super(Playlists, self).Menu(songs, songlist, library)
        model, rows = songlist.get_selection().get_selected_rows()
        iters = map(model.get_iter, rows)
        i = qltk.MenuItem(_("_Remove from Playlist"), Gtk.STOCK_REMOVE)
        i.connect_object('activate', self.__remove, iters, model)
        i.set_sensitive(bool(self.__view.get_selection().get_selected()[1]))
        menu.preseparate()
        menu.prepend(i)
        return menu

    __lists = Gtk.TreeModelSort(model=Gtk.ListStore(object))
    __lists.set_default_sort_func(lambda m, a, b, data: cmp(m[a][0], m[b][0]))

    def __init__(self, library, main):
        super(Playlists, self).__init__(spacing=6)
        self.__main = main
        self.__view = view = RCMHintedTreeView()
        self.__view.set_enable_search(True)
        self.__view.set_search_column(0)
        self.__view.set_search_equal_func(
            lambda model, col, key, iter, data:
            not model[iter][col].name.lower().startswith(key.lower()), None)
        self.__render = render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        render.connect('editing-started', self.__start_editing)
        render.connect('edited', self.__edited)
        col = Gtk.TreeViewColumn("Playlists", render)
        col.set_cell_data_func(render, Playlists.cell_data)
        view.append_column(col)
        view.set_model(self.__lists)
        view.set_rules_hint(True)
        view.set_headers_visible(False)
        swin = ScrolledWindow()
        swin.set_shadow_type(Gtk.ShadowType.IN)
        swin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        swin.add(view)
        self.pack_start(swin, True, True, 0)

        newpl = Gtk.Button(stock=Gtk.STOCK_NEW)
        newpl.connect('clicked', self.__new_playlist)
        importpl = qltk.Button(_("_Import"), Gtk.STOCK_ADD)
        importpl.connect('clicked', self.__import, library)
        hb = Gtk.HBox(spacing=6)
        hb.set_homogeneous(True)
        hb.pack_start(newpl, True, True, 0)
        hb.pack_start(importpl, True, True, 0)
        self.pack_start(Alignment(hb, left=3, bottom=3), False, True, 0)

        view.connect('popup-menu', self.__popup_menu, library)

        targets = [
            ("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP, DND_QL),
            ("text/uri-list", 0, DND_URI_LIST),
            ("text/x-moz-url", 0, DND_MOZ_URL)
        ]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]

        view.drag_dest_set(Gtk.DestDefaults.ALL, targets,
                           Gdk.DragAction.COPY)
        view.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, targets[:2],
                             Gdk.DragAction.COPY)
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

        self.connect('key-press-event', self.__key_pressed)

        for child in self.get_children():
            child.show_all()

    def __key_pressed(self, widget, event):
        if qltk.is_accel(event, "Delete"):
            model, iter = self.__view.get_selection().get_selected()
            if not iter:
                return False

            playlist = model[iter][0]
            dialog = ConfirmRemovePlaylistDialog(self, playlist)
            if dialog.run() == Gtk.ResponseType.YES:
                playlist.delete()
                model.get_model().remove(
                    model.convert_iter_to_child_iter(iter))
            return True
        elif qltk.is_accel(event, "F2"):
            model, iter = self.__view.get_selection().get_selected()
            if iter:
                self.__render.set_property('editable', True)
                self.__view.set_cursor(model.get_path(iter),
                                       self.__view.get_columns()[0],
                                       start_editing=True)
            return True
        return False

    def __check_current(self, model, path, iter):
        model, citer = self.__view.get_selection().get_selected()
        if citer and model.get_path(citer) == path:
            songlist = qltk.get_top_parent(self).songlist
            self.activate(resort=not songlist.is_sorted())

    def __drag_motion(self, view, ctx, x, y, time):
        targets = [t.name() for t in ctx.list_targets()]
        if "text/x-quodlibet-songs" in targets:
            view.set_drag_dest(x, y, into_only=True)
            return True
        else:
            # Highlighting the view itself doesn't work.
            view.get_parent().drag_highlight()
            return True

    def __drag_leave(self, view, ctx, time):
        view.get_parent().drag_unhighlight()

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
        if tid == DND_QL:
            filenames = sel.get_data().split("\x00")
            songs = filter(None, map(library.get, filenames))
            if not songs:
                Gtk.drag_finish(ctx, False, False, etime)
                return
            try:
                path, pos = view.get_dest_row_at_pos(x, y)
            except TypeError:
                playlist = Playlist.fromsongs(PLAYLISTS, songs, library)
                GLib.idle_add(self.__select_playlist, playlist)
            else:
                playlist = model[path][0]
                playlist.extend(songs)
            Playlists.changed(playlist)
            Gtk.drag_finish(ctx, True, False, etime)
        else:
            if tid == DND_URI_LIST:
                uri = sel.get_uris()[0]
                name = os.path.basename(uri)
            elif tid == DND_MOZ_URL:
                data = sel.get_data()
                uri, name = data.decode('utf16', 'replace').split('\n')
            else:
                Gtk.drag_finish(ctx, False, False, etime)
                return
            name = name or os.path.basename(uri) or _("New Playlist")
            uri = uri.encode('utf-8')
            try:
                sock = urllib.urlopen(uri)
                f = NamedTemporaryFile()
                f.write(sock.read())
                f.flush()
                if uri.lower().endswith('.pls'):
                    playlist = ParsePLS(f.name, library=library)
                elif uri.lower().endswith('.m3u'):
                    playlist = ParseM3U(f.name, library=library)
                else:
                    raise IOError
                library.add_filename(playlist)
                if name:
                    playlist.rename(name)
                Playlists.changed(playlist)
                Gtk.drag_finish(ctx, True, False, etime)
            except IOError:
                Gtk.drag_finish(ctx, False, False, etime)
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
            type_ = Gdk.atom_intern("text/x-quodlibet-songs", True)
            sel.set(type_, 8, "\x00".join(filenames))
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
                if s in unique:
                    dupes.append(s)
                else:
                    unique.add(s)
            if len(dupes) < 1:
                print_d("No duplicates in this playlist")
                return
            dialog = ConfirmRemoveDuplicatesDialog(self, playlist, len(dupes))
            if dialog.run() == Gtk.ResponseType.YES:
                playlist.remove_songs(dupes, library, True)
                Playlists.changed(playlist)
                self.activate()

        de_dupe = Gtk.MenuItem(_("Remove Duplicates"))
        de_dupe.connect_object('activate', _de_duplicate, model, itr)
        de_dupe.set_sensitive(not model[itr][0].has_duplicates())
        menu.prepend(de_dupe)

        def _shuffle(model, itr):
            playlist = model[itr][0]
            playlist.shuffle()
            self.activate()

        shuffle = Gtk.MenuItem(_("_Shuffle"), use_underline=True)
        shuffle .connect_object('activate', _shuffle, model, itr)
        shuffle.set_sensitive(bool(len(model[itr][0])))
        menu.prepend(shuffle)
        menu.prepend(SeparatorMenuItem())

        def _remove(model, itr):
            playlist = model[itr][0]
            dialog = ConfirmRemovePlaylistDialog(self, playlist)
            if dialog.run() == Gtk.ResponseType.YES:
                playlist.delete()
                model.get_model().remove(
                    model.convert_iter_to_child_iter(itr))

        rem = Gtk.ImageMenuItem(Gtk.STOCK_DELETE, use_stock=True)
        rem.connect_object('activate', _remove, model, itr)
        menu.prepend(rem)

        def _rename(path):
            self.__render.set_property('editable', True)
            view.set_cursor(path, view.get_columns()[0], start_editing=True)

        ren = qltk.MenuItem(_("_Rename"), Gtk.STOCK_EDIT)
        qltk.add_fake_accel(ren, "F2")
        ren.connect_object('activate', _rename, model.get_path(itr))
        menu.prepend(ren)

        menu.show_all()
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

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
        try:
            self.__lists[path][0].rename(newname)
        except ValueError, s:
            qltk.ErrorMessage(
                None, _("Unable to rename playlist"), s).run()
        else:
            row = self.__lists[path]
            self.__lists.row_changed(row.path, row.iter)
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
        except Exception:
            return
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
            GLib.idle_add(self.__select_playlist, playlist)
        if playlist:
            Playlists.changed(playlist, refresh=False)

browsers = [Playlists]
