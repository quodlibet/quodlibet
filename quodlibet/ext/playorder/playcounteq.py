# Copyright 2012-2016 Ryan "ZDBioHazard" Turner <zdbiohazard2@gmail.com>
#           2016-2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import math
import random

from quodlibet import _
from quodlibet.order.reorder import Reorder
from quodlibet.plugins.playorder import ShufflePlugin
from quodlibet.order import OrderRemembered
from quodlibet.qltk import Icons


class PlaycountEqualizer(ShufflePlugin, OrderRemembered):
    PLUGIN_ID = "playcounteq"
    PLUGIN_NAME = _("Playcount Equalizer")
    PLUGIN_DESC = _("Adds a shuffle mode "
                    "that prefers songs with fewer total plays.")
    PLUGIN_ICON = Icons.MEDIA_PLAYLIST_SHUFFLE
    display_name = _("Prefer less played")

    priority = Reorder.priority

    # Select the next track.
    def next(self, playlist, current):
        super().next(playlist, current)

        remaining = self.remaining(playlist)

        # Don't try to search through an empty / played playlist.
        if len(remaining) <= 0:
            return None

        # Set-up the search information.
        max_count = max([song('~#playcount') for song in remaining.values()])
        weights = {i: max_count - song('~#playcount')
                   for i, song in remaining.items()}
        choice = int(max(1, math.ceil(sum(weights) * random.random())))

        # Search for a track.
        for i, weight in weights.items():
            choice -= weight
            if choice <= 0:
                return playlist.get_iter([i])
        else:  # This should only happen if all songs have equal play counts.
            return playlist.get_iter([random.choice(list(remaining.keys()))])
