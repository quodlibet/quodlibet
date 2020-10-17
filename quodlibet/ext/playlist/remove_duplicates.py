# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet.formats import AudioFile
from quodlibet import print_d, ngettext, _

from quodlibet import qltk

from quodlibet.plugins.playlist import PlaylistPlugin
from quodlibet.qltk import Icons
from gi.repository import Gtk


class RemoveDuplicates(PlaylistPlugin):
    PLUGIN_ID = "Remove Playlist Duplicates"
    PLUGIN_NAME = _("Remove Playlist Duplicates")
    PLUGIN_DESC = _("Removes duplicate entries in a playlist.")
    PLUGIN_ICON = Icons.EDIT_CLEAR

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

        super().__init__(
            Gtk.MessageType.WARNING, parent, title, description,
            Gtk.ButtonsType.NONE)

        self.add_button(_("_Cancel"), Gtk.ResponseType.CANCEL)
        self.add_icon_button(_("_Remove"), Icons.LIST_REMOVE,
                             Gtk.ResponseType.YES)
