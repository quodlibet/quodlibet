# Copyright 2014-2017 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk, Pango, GObject

from quodlibet import app
from quodlibet import ngettext, _
from quodlibet import qltk
from quodlibet.browsers.playlists.util import GetPlaylistName, PLAYLISTS
from quodlibet.qltk import SeparatorMenuItem, get_menu_item_top_parent, Icons
from quodlibet.util.collection import Playlist, FileBackedPlaylist


class PlaylistMenu(Gtk.Menu):
    __gsignals__ = {
        'new': (GObject.SignalFlags.RUN_LAST, None, (object,)),
    }

    def __init__(self, songs, playlists):
        super(PlaylistMenu, self).__init__()
        i = Gtk.MenuItem(label=_(u"_New Playlist…"), use_underline=True)
        i.connect('activate', self._on_new_playlist_activate, songs)
        self.append(i)
        self.append(SeparatorMenuItem())
        self.set_size_request(int(i.size_request().width * 2), -1)

        for playlist in playlists:
            name = playlist.name
            i = Gtk.CheckMenuItem(label=name)
            some, all = playlist.has_songs(songs)
            i.set_active(some)
            i.set_inconsistent(some and not all)
            i.get_child().set_ellipsize(Pango.EllipsizeMode.END)
            i.connect(
                'activate', self._on_toggle_playlist_activate, playlist, songs)
            self.append(i)

    def _on_new_playlist_activate(self, item, songs):
        parent = get_menu_item_top_parent(item)
        title = Playlist.suggested_name_for(songs)
        title = self._get_new_name(parent, title)
        if title is None:
            return
        playlist = FileBackedPlaylist.new(PLAYLISTS, title,
                                          library=app.library)
        playlist.extend(songs)
        self._emit_new(playlist)

    def _get_new_name(self, parent, title):
        """Ask the user for a name for the new playlist"""
        return GetPlaylistName(qltk.get_top_parent(parent)).run(title)

    def _emit_new(self, playlist):
        # TODO: signals directly from a new playlist library (#518)
        self.emit('new', playlist)

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

        desc = ngettext("What do you want to do with that %d song?",
                        "What do you want to do with those %d songs?",
                        len(songs)) % len(songs)

        title = _("Confirm action for playlist \"%s\"") % playlist.name
        super(ConfirmMultipleSongsAction, self).__init__(
            Gtk.MessageType.QUESTION, parent, title, desc,
            Gtk.ButtonsType.NONE)

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(_("_Add"), Icons.LIST_ADD, self.ADD)
        self.add_icon_button(_("_Remove"), Icons.LIST_REMOVE, self.REMOVE)
