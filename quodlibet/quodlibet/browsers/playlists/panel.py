# -*- coding: utf-8 -*-
# Copyright 2017 Didier Villevalois
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Pango

from quodlibet import _
from quodlibet import qltk
from quodlibet.browsers.playlists.menu import ConfirmMultipleSongsAction
from quodlibet.browsers.playlists.util import GetPlaylistName, PLAYLISTS
from quodlibet.qltk import Icons, get_top_parent
from quodlibet.qltk.edittags import AudioFileGroup
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.qltk.x import ScrolledWindow
from quodlibet.util.collection import Playlist, FileBackedPlaylist


class PlaylistPanel(Gtk.VBox):
    def __init__(self, parent, library):
        super(PlaylistPanel, self).__init__(spacing=12)
        self.title = _("Playlists")
        self.set_border_width(12)

        self.__view = self._create_playlist_view()

        swin = ScrolledWindow()
        swin.set_shadow_type(Gtk.ShadowType.IN)
        swin.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        swin.add(self.__view)
        self.pack_start(swin, True, True, 0)

        buttonbox = self._create_buttons()
        self.pack_start(buttonbox, False, True, 0)

        # The library may actually be a librarian; if it is, use it,
        # otherwise find the real librarian.
        self.librarian = getattr(library, 'librarian', library)

        model = ObjectStore()
        self.__view.set_model(model)
        self._reload_playlists()

        parent.connect('changed', self.__parent_changed)
        self._parent = parent

        for child in self.get_children():
            child.show_all()

    def _create_playlist_view(self):
        # Create playlist view
        view = RCMHintedTreeView()
        view.set_enable_search(True)
        view.set_search_column(0)
        view.set_search_equal_func(
            lambda model, col, key, iter, data:
            not model[iter][col].name.lower().startswith(key.lower()), None)

        # Toggle checkbox column
        render = Gtk.CellRendererToggle()

        def toggle_cell_data(col, render, model, iter_, data):
            playlist = model.get_value(iter_)
            songs = self.__songinfo.songs
            some, all = playlist.has_songs(songs)
            render.set_active(some)
            render.set_property('inconsistent', some and not all)
            render.notify('inconsistent')

        render.connect('toggled', self._on_toggle_playlist_activate)
        column = Gtk.TreeViewColumn("toggled", render)
        column.set_cell_data_func(render, toggle_cell_data)
        view.append_column(column)

        # Playlist name column
        render = Gtk.CellRendererText()
        render.set_padding(3, 3)
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        render.set_property('editable', False)

        def name_cell_data(col, render, model, iter_, data):
            playlist = model.get_value(iter_)
            render.set_property('text', playlist.name)

        column = Gtk.TreeViewColumn("playlist", render)
        column.set_cell_data_func(render, name_cell_data)
        view.append_column(column)

        view.set_rules_hint(True)
        view.set_headers_visible(False)
        view.get_selection().set_mode(Gtk.SelectionMode.NONE)

        view.connect('row-activated', self._on_playlist_row_activated)

        return view

    def _create_buttons(self):
        buttonbox = Gtk.HBox(spacing=18)

        bbox1 = Gtk.HButtonBox()
        bbox1.set_spacing(6)
        bbox1.set_layout(Gtk.ButtonBoxStyle.START)

        # New Playlist button
        new_playlist = qltk.Button(_("_New Playlist…"), Icons.LIST_ADD)
        new_playlist.set_focus_on_click(False)
        new_playlist.connect('clicked', self._on_new_playlist)
        bbox1.pack_start(new_playlist, True, True, 0)

        buttonbox.pack_start(bbox1, True, True, 0)

        return buttonbox

    def _reload_playlists(self):
        from quodlibet.browsers.playlists import PlaylistsBrowser
        self.__playlists = PlaylistsBrowser.playlists()

        model = self.__view.get_model()
        model.clear()
        model.append_many(self.__playlists)

    def __parent_changed(self, parent, songs):
        if songs is not None:
            self.__songinfo = AudioFileGroup(songs)
        self._reload_playlists()

    def _update_browser(self, playlist):
        from quodlibet.browsers.playlists import PlaylistsBrowser
        PlaylistsBrowser.changed(playlist)

    def _on_toggle_playlist_activate(self, render, path):
        self._toggle_playlist(path)

    def _on_playlist_row_activated(self, view, path, column):
        self._toggle_playlist(path)

    def _toggle_playlist(self, path):
        model = self.__view.get_model()
        iter_ = model.get_iter(path)
        playlist = model.get_value(iter_)

        songs = self.__songinfo.songs

        has_some, has_all = playlist.has_songs(songs)
        if has_all:
            playlist.remove_songs(songs)
        elif has_some:
            resp = ConfirmMultipleSongsAction(get_top_parent(self._parent),
                                              playlist, songs).run()
            if resp == ConfirmMultipleSongsAction.REMOVE:
                playlist.remove_songs(songs)
            elif resp == ConfirmMultipleSongsAction.ADD:
                playlist.extend(songs)
        else:
            playlist.extend(songs)

        self._update_browser(playlist)

    def _on_new_playlist(self, button):
        parent = get_top_parent(self._parent)

        songs = self.__songinfo.songs

        title = Playlist.suggested_name_for(songs)
        title = self._get_new_name(parent, title)
        if title is None:
            return
        playlist = FileBackedPlaylist.new(PLAYLISTS, title)
        playlist.extend(songs)

        self._update_browser(playlist)
        self._reload_playlists()

    def _get_new_name(self, parent, title):
        """Ask the user for a name for the new playlist"""
        return GetPlaylistName(qltk.get_top_parent(parent)).run(title)
