# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Pango

from quodlibet import qltk
from quodlibet.browsers.playlists import PlaylistsBrowser
from quodlibet.browsers.playlists.util import GetPlaylistName, PLAYLISTS
from quodlibet.qltk import SeparatorMenuItem
from quodlibet.util.collection import Playlist


class PlaylistMenu(Gtk.Menu):
    def __init__(self, songs, parent=None):
        super(PlaylistMenu, self).__init__()
        i = Gtk.MenuItem(label=_("_New Playlist" + "..."), use_underline=True)
        i.connect_object('activate', self.__add_to_new_playlist, songs, parent)
        self.append(i)
        self.append(SeparatorMenuItem())
        self.set_size_request(int(i.size_request().width * 2), -1)

        for playlist in PlaylistsBrowser.playlists():
            name = playlist.name
            i = Gtk.CheckMenuItem(name)
            some, all = playlist.has_songs(songs)
            i.set_active(some)
            i.set_inconsistent(some and not all)
            i.get_child().set_ellipsize(Pango.EllipsizeMode.END)
            i.connect_object(
                'activate', self.__toggle_playlist, playlist, songs, parent)
            self.append(i)

    @staticmethod
    def __toggle_playlist(playlist, songs, parent):
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
        PlaylistsBrowser.changed(playlist)

    @staticmethod
    def __add_to_new_playlist(songs, parent):
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
        PlaylistMenu.__add_songs_to_playlist(playlist, songs)

    @staticmethod
    def __add_songs_to_playlist(playlist, songs):
        playlist.extend(songs)
        PlaylistsBrowser.changed(playlist)


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

        self.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                         Gtk.STOCK_ADD, self.ADD,
                         Gtk.STOCK_REMOVE, self.REMOVE)
