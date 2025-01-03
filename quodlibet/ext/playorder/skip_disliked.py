# Copyright 2016-20 Nick Boultbee
#              2017 Jason Heard
#              2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

from quodlibet import _, print_d
from quodlibet.order import OrderInOrder
from quodlibet.plugins import PluginConfig
from quodlibet.plugins.playorder import ShufflePlugin
from quodlibet.qltk import Icons

pconfig = PluginConfig("skip_songs")
pconfig.defaults.set("threshold", 0.0)


class SkipDisliked(ShufflePlugin, OrderInOrder):
    PLUGIN_ID = "skip_songs"
    PLUGIN_NAME = _("Skip Disliked Tracks")
    PLUGIN_ICON = Icons.GO_JUMP
    PLUGIN_DESC = _(
        "Adds a play order (shuffle) mode that plays in order, "
        "but skips tracks with a rating "
        "below (or equal to) a given threshold."
    )
    display_name = _("Skip disliked tracks")
    accelerated_name = _("Skip _disliked tracks")

    @classmethod
    def PluginPreferences(cls, window):
        vb = Gtk.VBox(spacing=10)
        vb.set_border_width(0)

        adj = Gtk.Adjustment.new(pconfig.getfloat("threshold"), 0, 1.0, 0.01, 0.01, 0.0)
        fb_spin = Gtk.SpinButton(adjustment=adj)
        fb_spin.set_digits(2)

        def on_changed(button):
            pconfig.set("threshold", button.get_value())

        fb_spin.connect("changed", on_changed)

        vb.add(fb_spin)
        vb.show_all()
        return vb

    def next(self, playlist, current):
        next_ = super().next(playlist, current)

        while next_ is not None and self._should_skip(playlist, next_):
            next_ = super().next(playlist, next_)

        return next_

    def previous(self, playlist, current):
        previous = super().previous(playlist, current)
        is_first = False

        while (
            not is_first
            and previous is not None
            and self._should_skip(playlist, previous)
        ):
            previous = super().previous(playlist, previous)
            is_first = playlist.get_path(previous).get_indices()[0] == 0

        return previous

    def _should_skip(self, playlist, song_iter):
        song = playlist.get_value(song_iter)

        if not song.has_rating:
            return False

        rating = song("~#rating")
        threshold = pconfig.getfloat("threshold")

        if rating <= threshold:
            print_d(f"Rating is {rating:f} <= {threshold:f}; skipping...")
            return True
        return False
