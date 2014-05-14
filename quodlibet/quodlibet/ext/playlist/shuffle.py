# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from quodlibet.plugins.playlist import PlaylistPlugin
from gi.repository import Gtk


class Shuffle(PlaylistPlugin):
    PLUGIN_ID = "Shuffle Playlist"
    PLUGIN_NAME = _("Shuffle Playlist")
    PLUGIN_DESC = _("Randomly shuffles a playlist")
    PLUGIN_ICON = 'gtk-execute'
    PLUGIN_VERSION = "1.0"

    def plugin_playlist(self, playlist):
        playlist.shuffle()
        return True

    def plugin_handles(self, playlists):
        return len(playlists) == 1 and len(playlists[0].songs) > 1
