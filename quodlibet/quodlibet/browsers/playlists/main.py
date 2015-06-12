# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#    2012 - 2015 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import urllib
from gi.repository import Gtk, GLib, Pango, Gdk
from tempfile import NamedTemporaryFile
from quodlibet.plugins.playlist import PLAYLIST_HANDLER

from quodlibet import config
from quodlibet.browsers._base import Browser
from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.songlist import SongList
from quodlibet.query import Query
from quodlibet.util import connect_obj
from quodlibet.util.path import get_home_dir
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.qltk.models import ObjectStore, ObjectModelSort
from quodlibet.qltk.x import ScrolledWindow, Align

from .util import *


DND_QL, DND_URI_LIST, DND_MOZ_URL = range(3)


class PlaylistsBrowser(Browser):

    name = _("Playlists")
    accelerated_name = _("_Playlists")
    priority = 2
    replaygain_profiles = ["track"]

    def pack(self, songpane):
        self._main_box.pack1(self, True, False)
        self._rh_box = rhbox = Gtk.VBox(spacing=6)
        align = Align(self._sb_box, left=0, right=6, top=6)
        rhbox.pack_start(align, False, True, 0)
        rhbox.pack_start(songpane, True, True, 0)
        self._main_box.pack2(rhbox, True, False)
        rhbox.show()
        align.show_all()
        return self._main_box

    def unpack(self, container, songpane):
        self._rh_box.remove(songpane)
        container.remove(self._rh_box)
        container.remove(self)

    @classmethod
    def init(klass, library):
        model = klass.__lists.get_model()
        for playlist in os.listdir(PLAYLISTS):
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
            if playlist.remove_songs(songs):
                PlaylistsBrowser.changed(playlist)

    @classmethod
    def __added(klass, library, songs):
        filenames = {song("~filename") for song in songs}
        for playlist in klass.playlists():
            if playlist.add_songs(filenames, library):
                PlaylistsBrowser.changed(playlist)

    @classmethod
    def __changed(klass, library, songs):
        for playlist in klass.playlists():
            for song in songs:
                if song in playlist.songs:
                    PlaylistsBrowser.changed(playlist, refresh=False)
                    break

    @staticmethod
    def cell_data(col, render, model, iter, data):
        render.markup = model[iter][0].format()
        render.set_property('markup', render.markup)

    def Menu(self, songs, library, items):
        songlist = qltk.get_top_parent(self).songlist
        model, iters = self.__get_selected_songs(songlist)
        item = qltk.MenuItem(_("_Remove from Playlist"), Gtk.STOCK_REMOVE)
        qltk.add_fake_accel(item, "Delete")
        connect_obj(item, 'activate', self.__remove, iters, model)
        item.set_sensitive(bool(self.__view.get_selection().get_selected()[1]))

        items.append([item])
        menu = super(PlaylistsBrowser, self).Menu(songs, library, items)
        return menu

    def __get_selected_songs(self, songlist):
        model, rows = songlist.get_selection().get_selected_rows()
        iters = map(model.get_iter, rows)
        return model, iters

    __lists = ObjectModelSort(model=ObjectStore())
    __lists.set_default_sort_func(lambda m, a, b, data: cmp(m[a][0], m[b][0]))

    def __init__(self, library):
        super(PlaylistsBrowser, self).__init__(spacing=6)
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.__render = self.__create_cell_renderer()
        self.__view = view = self.__create_playlists_view(self.__render)
        self.__embed_in_scrolledwin(view)
        self.__configure_buttons(library)
        self.__configure_dnd(view, library)
        self.__connect_signals(view, library)
        self._sb_box = self.__create_searchbar(library)
        self._main_box = self.__create_box()
        self.show_all()
        self._query = None

        for child in self.get_children():
            child.show_all()

    def __destroy(self, *args):
        del self._sb_box

    def __create_box(self):
        box = qltk.ConfigRHPaned("browsers", "playlistsbrowser_pos", 0.4)
        box.show_all()
        return box

    def __create_searchbar(self, library):
        self.accelerators = Gtk.AccelGroup()
        completion = LibraryTagCompletion(library.librarian)
        sbb = SearchBarBox(completion=completion,
                           accel_group=self.accelerators)
        sbb.connect('query-changed', self.__text_parse)
        sbb.connect('focus-out', self.__focus)
        return sbb

    def __embed_in_scrolledwin(self, view):
        swin = ScrolledWindow()
        swin.set_shadow_type(Gtk.ShadowType.IN)
        swin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        swin.add(view)
        self.pack_start(swin, True, True, 0)

    def __configure_buttons(self, library):
        newpl = qltk.Button(_("_New"), Gtk.STOCK_NEW, Gtk.IconSize.MENU)
        newpl.connect('clicked', self.__new_playlist)
        importpl = qltk.Button(_("_Import"), Gtk.STOCK_ADD, Gtk.IconSize.MENU)
        importpl.connect('clicked', self.__import, library)
        hb = Gtk.HBox(spacing=6)
        hb.set_homogeneous(True)
        hb.pack_start(newpl, True, True, 0)
        hb.pack_start(importpl, True, True, 0)
        self.pack_start(Align(hb, left=3, bottom=3), False, True, 0)

    def __create_playlists_view(self, render):
        view = RCMHintedTreeView()
        view.set_enable_search(True)
        view.set_search_column(0)
        view.set_search_equal_func(
            lambda model, col, key, iter, data:
            not model[iter][col].name.lower().startswith(key.lower()), None)
        col = Gtk.TreeViewColumn("Playlists", render)
        col.set_cell_data_func(render, PlaylistsBrowser.cell_data)
        view.append_column(col)
        view.set_model(self.__lists)
        view.set_rules_hint(True)
        view.set_headers_visible(False)
        return view

    def __configure_dnd(self, view, library):
        targets = [
            ("text/x-quodlibet-songs", Gtk.TargetFlags.SAME_APP, DND_QL),
            ("text/uri-list", 0, DND_URI_LIST),
            ("text/x-moz-url", 0, DND_MOZ_URL)
        ]
        targets = [Gtk.TargetEntry.new(*t) for t in targets]
        view.drag_dest_set(Gtk.DestDefaults.ALL, targets, Gdk.DragAction.COPY)
        view.drag_source_set(Gdk.ModifierType.BUTTON1_MASK, targets[:2],
                             Gdk.DragAction.COPY)
        view.connect('drag-data-received', self.__drag_data_received, library)
        view.connect('drag-data-get', self.__drag_data_get)
        view.connect('drag-motion', self.__drag_motion)
        view.connect('drag-leave', self.__drag_leave)

    def __connect_signals(self, view, library):
        view.connect('row-activated', lambda *x: self.songs_activated())
        view.connect('popup-menu', self.__popup_menu, library)
        view.get_selection().connect('changed', self.activate)
        model = view.get_model()
        s = model.connect('row-changed', self.__check_current)
        connect_obj(self, 'destroy', model.disconnect, s)
        self.connect('key-press-event', self.__key_pressed)

    def __create_cell_renderer(self):
        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        render.connect('editing-started', self.__start_editing)
        render.connect('edited', self.__edited)
        return render

    def key_pressed(self, event):
        if qltk.is_accel(event, "Delete"):
            self.__handle_songlist_delete()
            return True
        return False

    def __handle_songlist_delete(self, *args):
        songlist = qltk.get_top_parent(self).songlist
        model, iters = self.__get_selected_songs(songlist)
        self.__remove(iters, model)

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
            for iter_remove in iters:
                smodel.remove(iter_remove)
            playlist = model[iter][0]
            # Calling playlist.remove_songs(songs) won't remove the right ones
            # if there are duplicates
            playlist.clear()
            playlist.extend([row[0] for row in smodel])
            PlaylistsBrowser.changed(playlist)
            self.activate()

    def __drag_data_received(self, view, ctx, x, y, sel, tid, etime, library):
        # TreeModelSort doesn't support GtkTreeDragDestDrop.
        view.emit_stop_by_name('drag-data-received')
        model = view.get_model()
        if tid == DND_QL:
            filenames = qltk.selection_get_filenames(sel)
            songs = filter(None, map(library.get, filenames))
            if not songs:
                Gtk.drag_finish(ctx, False, False, etime)
                return
            try:
                path, pos = view.get_dest_row_at_pos(x, y)
            except TypeError:
                playlist = Playlist.fromsongs(PLAYLISTS, songs, library)
                GLib.idle_add(self._select_playlist, playlist)
            else:
                playlist = model[path][0]
                playlist.extend(songs)
            PlaylistsBrowser.changed(playlist)
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
                    playlist = parse_pls(f.name, library=library)
                elif uri.lower().endswith('.m3u'):
                    playlist = parse_m3u(f.name, library=library)
                else:
                    raise IOError
                library.add_filename(playlist)
                if name:
                    playlist.rename(name)
                PlaylistsBrowser.changed(playlist)
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
            qltk.selection_set_songs(sel, songs)
        else:
            sel.set_uris([song("~uri") for song in songs])

    def _select_playlist(self, playlist):
        view = self.__view
        model = view.get_model()
        for row in model:
            if row[0] is playlist:
                view.get_selection().select_iter(row.iter)

    def __popup_menu(self, view, library):
        model, itr = view.get_selection().get_selected()
        if itr is None:
            return
        songs = list(model[itr][0])
        songs = filter(lambda s: isinstance(s, AudioFile), songs)
        menu = SongsMenu(library, songs,
                         playlists=False, remove=False,
                         ratings=False)
        menu.preseparate()

        def _remove(model, itr):
            playlist = model[itr][0]
            dialog = ConfirmRemovePlaylistDialog(self, playlist)
            if dialog.run() == Gtk.ResponseType.YES:
                playlist.delete()
                model.get_model().remove(
                    model.convert_iter_to_child_iter(itr))

        rem = Gtk.ImageMenuItem(Gtk.STOCK_DELETE, use_stock=True)
        connect_obj(rem, 'activate', _remove, model, itr)
        menu.prepend(rem)

        def _rename(path):
            self.__render.set_property('editable', True)
            view.set_cursor(path, view.get_columns()[0], start_editing=True)

        ren = qltk.MenuItem(_("_Rename"), Gtk.STOCK_EDIT)
        qltk.add_fake_accel(ren, "F2")
        connect_obj(ren, 'activate', _rename, model.get_path(itr))
        menu.prepend(ren)

        playlist = model[itr][0]
        PLAYLIST_HANDLER.populate_menu(menu, library, self, [playlist])
        menu.show_all()
        return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __focus(self, widget, *args):
        qltk.get_top_parent(widget).songlist.grab_focus()

    def __text_parse(self, bar, text):
        self.activate()

    def _get_text(self):
        return self._sb_box.get_text()

    def _set_text(self, text):
        self._sb_box.set_text(text)

    def activate(self, widget=None, resort=True):
        songs = self._get_playlist_songs()

        text = self._get_text()
        # TODO: remove static dependency on Query
        if Query.is_parsable(text):
            self._query = Query(text, SongList.star)
            songs = self._query.filter(songs)
        GLib.idle_add(self.songs_selected, songs, resort)

    def _get_playlist_songs(self):
        model, iter = self.__view.get_selection().get_selected()
        songs = iter and list(model[iter][0]) or []
        songs = filter(lambda s: isinstance(s, AudioFile), songs)
        return songs

    def can_filter_text(self):
        return True

    def filter_text(self, text):
        self._set_text(text)
        self.activate()

    def get_filter_text(self):
        return self._get_text()

    def can_filter(self, key):
        # TODO: special-case the ~playlists tag maybe?
        return super(PlaylistsBrowser, self).can_filter(key)

    def finalize(self, restore):
        config.set("browsers", "query_text", "")

    def unfilter(self):
        self.filter_text("")

    def active_filter(self, song):
        return (song in self._get_playlist_songs()
                and (self._query is None or self._query.search(song)))

    def save(self):
        model, iter = self.__view.get_selection().get_selected()
        name = iter and model[iter][0].name or ""
        config.set("browsers", "playlist", name)
        text = self._get_text()
        config.set("browsers", "query_text", text)

    def __new_playlist(self, activator):
        playlist = Playlist.new(PLAYLISTS)
        self.__lists.get_model().append(row=[playlist])
        self._select_playlist(playlist)

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

    def __import(self, activator, library):
        filt = lambda fn: fn.endswith(".pls") or fn.endswith(".m3u")
        from quodlibet.qltk.chooser import FileChooser
        chooser = FileChooser(self, _("Import Playlist"), filt, get_home_dir())
        files = chooser.run()
        chooser.destroy()
        for filename in files:
            if filename.endswith(".m3u"):
                playlist = parse_m3u(filename, library=library)
            elif filename.endswith(".pls"):
                playlist = parse_pls(filename, library=library)
            else:
                qltk.ErrorMessage(
                    qltk.get_top_parent(self),
                    _("Unable to import playlist"),
                    _("Quod Libet can only import playlists in the M3U "
                      "and PLS formats.")).run()
                return
            PlaylistsBrowser.changed(playlist)
            library.add(playlist)

    def restore(self):
        try:
            name = config.get("browsers", "playlist")
        except config.Error as e:
            print_d("Couldn't get last playlist from config: %s" % e)
        else:
            self.__view.select_by_func(lambda r: r[0].name == name, one=True)
        try:
            text = config.get("browsers", "query_text")
        except config.Error as e:
            print_d("Couldn't get last search string from config: %s" % e)
        else:
            self._set_text(text)

    can_reorder = True

    def reordered(self, songs):
        model, iter = self.__view.get_selection().get_selected()
        playlist = None
        if iter:
            playlist = model[iter][0]
            playlist[:] = songs
        elif songs:
            playlist = Playlist.fromsongs(PLAYLISTS, songs)
            GLib.idle_add(self._select_playlist, playlist)
        if playlist:
            PlaylistsBrowser.changed(playlist, refresh=False)
