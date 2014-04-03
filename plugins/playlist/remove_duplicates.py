# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.formats._audio import AudioFile
from quodlibet.util.dprint import print_d

from quodlibet import qltk

from quodlibet.plugins.playlist import PlaylistPlugin
from gi.repository import Gtk


class RemoveDuplicates(PlaylistPlugin):
    PLUGIN_ID = "Remove Playlist Duplicates"
    PLUGIN_NAME = _("Remove Playlist Duplicates")
    PLUGIN_DESC = _("Remove duplicate entries in a playlist")
    PLUGIN_ICON = 'gtk-clear'
    PLUGIN_VERSION = "1.0"

    def plugin_handles(self, playlists):
        return len(playlists) == 1 and playlists[0].has_duplicates

    def plugin_playlist(self, playlist):
        songs = filter(lambda s: isinstance(s, AudioFile), playlist.songs)

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
            playlist.remove_songs(dupes, True)
            return True
        return False


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
                         Gtk.STOCK_REMOVE, Gtk.ResponseType.YES)
