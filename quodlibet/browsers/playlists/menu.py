# Copyright 2014-2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Gio, GLib

from quodlibet import ngettext, _
from quodlibet import qltk
from quodlibet.browsers.playlists.util import GetPlaylistName
from quodlibet.library.playlist import PlaylistLibrary
from quodlibet.qltk import Icons
from quodlibet.util.collection import Playlist


class PlaylistMenu:
    """Builds a "Playlists" submenu on a ``Gio.Menu`` model.

    Registers a "playlist-new" action plus one stateful toggle action per
    playlist on ``action_group`` (prefixed with ``prefix``). Rebuildable via
    :meth:`build` for callers whose song selection changes over time.
    """

    def __init__(
        self,
        songs,
        pl_lib: PlaylistLibrary,
        action_group: Gio.SimpleActionGroup,
        prefix: str,
        parent_getter=None,
    ):
        self.pl_lib = pl_lib
        self._action_group = action_group
        self._prefix = prefix
        self._parent_getter = parent_getter or (lambda: None)
        self._songs = songs
        self._playlist_action_names: list[str] = []

        self._new_action = Gio.SimpleAction.new("playlist-new", None)
        self._new_action.connect("activate", self._on_new_playlist)
        action_group.add_action(self._new_action)

        self._menu = Gio.Menu()
        self.build(songs)
        self.menu_item = Gio.MenuItem.new_submenu(_("Play_lists"), self._menu)

    @property
    def submenu(self) -> Gio.Menu:
        return self._menu

    def set_sensitive(self, sensitive: bool):
        self._new_action.set_enabled(sensitive)
        for name in self._playlist_action_names:
            self._action_group.lookup_action(name).set_enabled(sensitive)

    def build(self, songs):
        """(Re)build the submenu model and per-playlist toggle actions."""
        self._songs = songs

        for name in self._playlist_action_names:
            self._action_group.remove_action(name)
        self._playlist_action_names = []
        self._menu.remove_all()

        new_section = Gio.Menu()
        new_section.append(_("_New Playlist…"), f"{self._prefix}.playlist-new")
        self._menu.append_section(None, new_section)

        playlists_section = Gio.Menu()
        for i, playlist in enumerate(sorted(self.pl_lib or [])):
            name = f"playlist-{i}"
            some, _all = playlist.has_songs(songs)
            action = Gio.SimpleAction.new_stateful(name, None, GLib.Variant("b", some))
            action.connect("change-state", self._on_toggle_playlist, playlist)
            self._action_group.add_action(action)
            self._playlist_action_names.append(name)
            playlists_section.append(playlist.name, f"{self._prefix}.{name}")
        self._menu.append_section(None, playlists_section)

    def _on_new_playlist(self, action, _param):
        self._on_new_playlist_activate(self._parent_getter(), self._songs)

    def _on_new_playlist_activate(self, parent, songs) -> Playlist | None:
        title = Playlist.suggested_name_for(songs)
        title = self._get_new_name(parent, title)
        if title is None:
            return None
        return self.pl_lib.create_from_songs(songs, title=title)

    def _get_new_name(self, parent, title):
        """Ask the user for a name for the new playlist"""
        return GetPlaylistName(qltk.get_top_parent(parent)).run(title)

    def _on_toggle_playlist(self, action, _value, playlist):
        self._toggle_playlist(self._parent_getter(), playlist, self._songs)
        some, _all = playlist.has_songs(self._songs)
        action.set_state(GLib.Variant("b", some))

    def _toggle_playlist(self, parent, playlist, songs):
        has_some, has_all = playlist.has_songs(songs)
        if has_all:
            playlist.remove_songs(songs)
        elif has_some:
            resp = ConfirmMultipleSongsAction(parent, playlist, songs).run()
            if resp == ConfirmMultipleSongsAction.REMOVE:
                playlist.remove_songs(songs)
            elif resp == ConfirmMultipleSongsAction.ADD:
                playlist.extend(songs)
        else:
            playlist.extend(songs)


class ConfirmMultipleSongsAction(qltk.Message):
    """Dialog to ask the user what to do when selecting a playlist
    for multiple songs with a mix of inclusion"""

    ADD, REMOVE = range(2)

    def __init__(self, parent, playlist, songs):
        desc = ngettext(
            "What do you want to do with that %d song?",
            "What do you want to do with those %d songs?",
            len(songs),
        ) % len(songs)

        title = _('Confirm action for playlist "%s"') % playlist.name
        super().__init__(
            Gtk.MessageType.QUESTION, parent, title, desc, Gtk.ButtonsType.NONE
        )

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(_("_Add"), Icons.LIST_ADD, self.ADD)
        self.add_icon_button(_("_Remove"), Icons.LIST_REMOVE, self.REMOVE)
