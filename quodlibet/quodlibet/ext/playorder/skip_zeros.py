# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#           2017 Jason Heard
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

from gi.repository import Gtk

from quodlibet import _, print_d, qltk
from quodlibet.order import OrderInOrder
from quodlibet.plugins import PluginConfigMixin
from quodlibet.plugins.playorder import ShufflePlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.ccb import ConfigCheckButton


class SkipZeros(ShufflePlugin, OrderInOrder, PluginConfigMixin):
    PLUGIN_ID = "skip_songs"
    PLUGIN_NAME = _("Skip Songs")
    PLUGIN_ICON = Icons.GO_JUMP
    PLUGIN_DESC = _("Playback skips over songs with a rating of zero or with "
                    "a non-empty 'skip' tag unless they are explicitly "
                    "played.")

    _CFG_SKIP_BY_RATING = 'skip_by_rating'
    _CFG_SKIP_BY_TAG = 'skip_by_tag'

    @classmethod
    def PluginPreferences(self, window):
        vb = Gtk.VBox(spacing=10)
        vb.set_border_width(0)

        # Matching Option
        toggles = [
            (self._CFG_SKIP_BY_RATING, _("Skip Songs with _Rating of Zero")),
            (self._CFG_SKIP_BY_TAG,
             _("Skip Songs with a Non-Empty 'skip' _Tag")),
        ]
        vb2 = Gtk.VBox(spacing=6)
        for key, label in toggles:
            ccb = ConfigCheckButton(label, 'plugins', self._config_key(key))
            ccb.set_active(self.config_get_bool(key))
            vb2.pack_start(ccb, True, True, 0)

        frame = qltk.Frame(label=_("Skipping options"), child=vb2)
        vb.pack_start(frame, True, True, 0)

        vb.show_all()
        return vb

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
        if self.config_get_bool(self._CFG_SKIP_BY_RATING) and rating <= 0:
            shouldSkip = True
            print_d("Rating is %f; skipping..." % (rating))
        elif self.config_get_bool(self._CFG_SKIP_BY_TAG) and \
             song("skip") != '':
            shouldSkip = True
            print_d("Skip tag present; skipping...")

        return shouldSkip
