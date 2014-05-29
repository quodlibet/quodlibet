# Copyright 2014 Jan Path
#           2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk

from quodlibet import config
from quodlibet.qltk import GetStringDialog
from quodlibet.qltk.ratingsmenu import ConfirmRateMultipleDialog
from quodlibet.plugins.songsmenu import SongsMenuPlugin


class ExactRating(SongsMenuPlugin):
    PLUGIN_ID = "exact-rating"
    PLUGIN_NAME = _("Set Exact Rating")
    PLUGIN_DESC = _("Dialog to set rating of songs as number")

    def plugin_songs(self, songs):
        value = -1
        while not 0 <= value <= 1:
            input_string = GetStringDialog(
                self.plugin_window,
                self.PLUGIN_NAME,
                _("Please give your desired rating on a scale from 0 to 1"),
                Gtk.STOCK_APPLY
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
                self.plugin_window, count, value)
            if confirm_dialog.run() != Gtk.ResponseType.YES:
                return

        for song in songs:
            song["~#rating"] = value
