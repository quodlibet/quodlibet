# -*- coding: utf-8 -*-
# Copyright 2012-2016 Ryan "ZDBioHazard" Turner <zdbiohazard2@gmail.com>
#                2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import math
import random

from quodlibet.plugins.playorder import PlayOrderPlugin, PlayOrderShuffleMixin
from quodlibet.qltk import Icons


class PlaycountEqualizer(PlayOrderPlugin, PlayOrderShuffleMixin):
    PLUGIN_ID = "playcounteq"
    PLUGIN_NAME = _("Playcount Equalizer")
    PLUGIN_DESC = _("Shuffle, preferring songs with fewer total plays.")
    PLUGIN_ICON = Icons.VIEW_REFRESH

    # Select the next track.
    def next(self, playlist, current):
        super(PlaycountEqualizer, self).next(playlist, current)

        songs = playlist.get()
        # Don't try to search through an empty playlist.
        if len(songs) <= 0:
            return None

        # Set-up the search information.
        max_count = max([song('~#playcount') for song in songs])
        weights = [max_count - song('~#playcount') for song in songs]
        choice = int(max(1, math.ceil(sum(weights) * random.random())))

        # Search for a track.
        for i, weight in enumerate(weights):
            choice -= weight
            if choice <= 0:
                return playlist.get_iter([i])
        else:  # This should only happen if all songs have equal play counts.
            return playlist.get_iter([random.randint(0, len(songs) - 1)])
