# Copyright 2014 Jan Path
#           2014 Christoph Reiter
#           2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _
from quodlibet import config
from quodlibet.plugins.songshelpers import any_song
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk import Icons
from quodlibet.qltk.ratingsmenu import ConfirmRateMultipleDialog
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class ExactRating(SongsMenuPlugin):
    PLUGIN_ID = "exact-rating"
    PLUGIN_NAME = _("Set Exact Rating")
    PLUGIN_DESC = _("Allows setting the rating of songs with a number.")
    REQUIRES_ACTION = True
    PLUGIN_ICON = Icons.USER_BOOKMARKS

    plugin_handles = any_song(lambda s: s.can_change())

    def plugin_songs(self, songs):
        value = -1
        while not 0 <= value <= 1:
            input_string = GetStringDialog(
                self.plugin_window,
                self.PLUGIN_NAME,
                _("Please give your desired rating on a scale "
                  "from 0.0 to 1.0"),
                _("_Apply"),
                Icons.NONE
            ).run()

            if input_string is None:
                return

            try:
                value = float(input_string)
            except ValueError:
                continue

        count = len(songs)
        if (count > 1 and config.getboolean("browsers",
                "rating_confirm_multiple")):
            confirm_dialog = ConfirmRateMultipleDialog(
                self.plugin_window, _("Change _Rating"), count, value)
            if confirm_dialog.run() != Gtk.ResponseType.YES:
                return

        for song in songs:
            song["~#rating"] = value
