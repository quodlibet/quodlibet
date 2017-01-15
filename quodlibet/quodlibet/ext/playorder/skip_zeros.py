# -*- coding: utf-8 -*-
# Copyright 2010 Christoph Reiter
#           2016 Nick Boultbee
#           2017 Jason Heard
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

from quodlibet import _, print_d
from quodlibet.order import OrderInOrder
from quodlibet.plugins.playorder import ShufflePlugin
from quodlibet.qltk import Icons


class SkipZeros(ShufflePlugin, OrderInOrder):
    PLUGIN_ID = "skip_zeros"
    PLUGIN_NAME = _("Skip Zero Rated")
    PLUGIN_ICON = Icons.GO_JUMP
    PLUGIN_DESC = _("Playback skips over songs with a rating of zero unless "
                    "explicitly played.")


    def next(self, playlist, current):
        next = super(SkipZeros, self).next(playlist, current)

        while next is not None and self.shouldSkip(playlist, next):
            next = super(SkipZeros, self).next(playlist, next)

        return next


    def previous(self, playlist, current):
        previous = super(SkipZeros, self).previous(playlist, current)

        while previous is not None and self.shouldSkip(playlist, previous):
            previous = super(SkipZeros, self).previous(playlist, current)

        return previous


    def shouldSkip(self, playlist, song_iter):
        song_index = playlist.get_path(song_iter).get_indices()[0]
        song = playlist.get()[song_index]
        rating = song("~#rating")

        shouldSkip = False
        if rating <= 0:
            shouldSkip = True
            print_d("Rating is %f; skipping..." % (rating))
        elif song("skip") <> '':
            shouldSkip = True
            print_d("Skip tag present; skipping...")

        return shouldSkip

