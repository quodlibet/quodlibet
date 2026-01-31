# Copyright 2014-2021 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Pango

from quodlibet import ngettext, _
from quodlibet import qltk
from quodlibet.browsers.playlists.util import GetPlaylistName
from quodlibet.library.playlist import PlaylistLibrary
from quodlibet.qltk import SeparatorMenuItem, get_menu_item_top_parent, Icons
from quodlibet.util.collection import Playlist


class PlaylistMenu(Gtk.PopoverMenu):
    def __init__(self, songs, pl_lib: PlaylistLibrary):
        super().__init__()
        self.pl_lib = pl_lib
        i = Gtk.MenuItem(label=_("_New Playlist…"), use_underline=True)
        i.connect("activate", self._on_new_playlist_activate, songs)
        self.append(i)
        self.append(SeparatorMenuItem())
        self.set_size_request(int(i.size_request().width * 2), -1)

        for playlist in sorted(pl_lib):
            name = playlist.name
            i = Gtk.CheckMenuItem(label=name)
            some, all = playlist.has_songs(songs)
            i.set_active(some)
            i.set_inconsistent(some and not all)
            i.get_child().set_ellipsize(Pango.EllipsizeMode.END)
            i.connect("activate", self._on_toggle_playlist_activate, playlist, songs)
            self.append(i)

    def _on_new_playlist_activate(self, item, songs) -> Playlist | None:
        parent = get_menu_item_top_parent(item)
        title = Playlist.suggested_name_for(songs)
        title = self._get_new_name(parent, title)
        if title is None:
            return None
        return self.pl_lib.create_from_songs(songs, title=title)

    def _get_new_name(self, parent, title):
        """Ask the user for a name for the new playlist"""
        return GetPlaylistName(qltk.get_top_parent(parent)).run(title)

    def _on_toggle_playlist_activate(self, item, playlist, songs):
        parent = get_menu_item_top_parent(item)

        has_some, has_all = playlist.has_songs(songs)
        if has_all:
            playlist.remove_songs(songs)
        elif has_some:
            resp = ConfirmMultipleSongsAction(parent, playlist, songs).run()
            if resp == ConfirmMultipleSongsAction.REMOVE:
                playlist.remove_songs(songs)
            elif resp == ConfirmMultipleSongsAction.ADD:
                playlist.extend(songs)
            return
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
