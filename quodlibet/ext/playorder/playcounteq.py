# Copyright 2012-2016 Ryan "ZDBioHazard" Turner <zdbiohazard2@gmail.com>
#           2016-2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import math
import random

from gi.repository import Gtk

from quodlibet import _, print_d
from quodlibet.order.reorder import Reorder
from quodlibet.plugins import PluginConfigMixin
from quodlibet.plugins.playorder import ShufflePlugin
from quodlibet.order import OrderRemembered
from quodlibet.qltk import Icons


class PlaycountEqualizer(ShufflePlugin, OrderRemembered, PluginConfigMixin):
    PLUGIN_ID = "playcounteq"
    PLUGIN_NAME = _("Playcount Equalizer")
    PLUGIN_DESC = _("Adds a shuffle mode that prefers songs with fewer total plays.")
    PLUGIN_ICON = Icons.MEDIA_PLAYLIST_SHUFFLE
    display_name = _("Prefer less played")
    accelerated_name = _("Prefer _less played")

    priority = Reorder.priority

    _MAGNITUDE_DEFAULT = 1

    # Select the next track.
    def next(self, playlist, current):
        super().next(playlist, current)

        remaining = self.remaining(playlist)

        # Don't try to search through an empty / played playlist.
        if len(remaining) <= 0:
            return None

        mag_cfg = float(self.config_get("magnitude", self._MAGNITUDE_DEFAULT))
        # Adjusting input to range from 1 to 3
        # weights will be calculated as a power of this value.
        magn = (mag_cfg * 2.0) / 100.0 + 1.0

        # Set-up the search information.
        max_count = max([song("~#playcount") for song in remaining.values()])

        weights = {
            i: math.ceil(math.pow(max_count - song("~#playcount") + 1, magn))
            for i, song in remaining.items()
        }

        weights_sum = sum(weights.values())
        choice = int(max(1, math.ceil(weights_sum * random.random())))

        print_d(f"Weighted random: {choice} for the weights sum: {weights_sum}")

        # Search for a track.
        for i, weight in weights.items():
            choice -= weight
            if choice <= 0:
                return playlist.get_iter([i])
        else:  # This should only happen if all songs have equal play counts.
            return playlist.get_iter([random.choice(list(remaining.keys()))])

    @classmethod
    def PluginPreferences(cls, parent):
        def magnitude_changed(spin):
            cls.config_set("magnitude", int(spin.get_value_as_int()))

        vb = Gtk.VBox(spacing=10)
        vb.set_border_width(10)
        hbox = Gtk.HBox(spacing=6)
        lbl = Gtk.Label(label=_("Priority for less played tracks"))
        hbox.pack_start(lbl, False, True, 0)

        val = cls.config_get("magnitude", cls._MAGNITUDE_DEFAULT)

        spin = Gtk.SpinButton(adjustment=Gtk.Adjustment.new(int(val), 1, 100, 1, 10, 0))
        spin.connect("value-changed", magnitude_changed)
        hbox.pack_start(spin, False, True, 0)
        vb.pack_start(hbox, True, True, 0)
        vb.show_all()
        return vb
