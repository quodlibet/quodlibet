# Copyright 2016 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import contextlib

from gi.repository import GObject, Gtk

from quodlibet import _
from quodlibet import app
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons, get_children
from quodlibet.qltk.seekbutton import TimeLabel
from quodlibet.qltk.tracker import TimeTracker
from quodlibet.qltk import Align
from quodlibet.util import connect_destroy


class SeekBar(Gtk.Box):
    def __init__(self, player, library):
        super().__init__()

        self._elapsed_label = TimeLabel()
        self._remaining_label = TimeLabel()
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL)
        scale.set_adjustment(Gtk.Adjustment.new(0, 0, 0, 3, -15, 0))
        scale.set_draw_value(False)
        self._scale = scale

        self.append(Align(self._elapsed_label, border=6))
        self.append(scale)
        self.append(Align(self._remaining_label, border=6))
        for child in get_children(self):
            child.show_all()

        self._id = self._scale.connect("value-changed", self._on_user_changed, player)
        self._scale.connect("value-changed", self._on_scale_value_changed, player)

        self._tracker = TimeTracker(player)
        self._tracker.connect("tick", self._on_tick, player)

        connect_destroy(player, "seek", self._on_player_seek)
        connect_destroy(player, "song-started", self._on_song_started)
        connect_destroy(player, "notify::seekable", self._on_seekable_changed)

        connect_destroy(library, "changed", self._on_song_changed, player)

        self.connect("destroy", self._on_destroy)

        with self._inhibit():
            self._update(player)
        self._tracker.tick()

    def _on_destroy(self, *args):
        self._tracker = None

    @contextlib.contextmanager
    def _inhibit(self):
        with GObject.signal_handler_block(self._scale, self._id):
            yield

    def _on_user_changed(self, scale, player):
        if player.seekable:
            player.seek(scale.get_value() * 1000)

    def _on_scale_value_changed(self, scale, player):
        self._update(player)

    def _on_tick(self, tracker, player):
        position = player.get_position() // 1000
        with self._inhibit():
            self._scale.set_value(position)

    def _on_seekable_changed(self, player, *args):
        with self._inhibit():
            self._update(player)

    def _on_song_changed(self, library, songs, player):
        if player.info in songs:
            with self._inhibit():
                self._update(player)

    def _on_player_seek(self, player, song, ms):
        with self._inhibit():
            self._scale.set_value(ms // 1000)
            self._update(player)

    def _on_song_started(self, player, song):
        with self._inhibit():
            self._scale.set_value(0)
            self._update(player)

    def _update(self, player):
        if player.info:
            self._scale.set_range(0, player.info("~#length"))
        else:
            self._scale.set_range(0, 1)

        if not player.seekable:
            self._scale.set_value(0)

        value = self._scale.get_value()
        max_ = self._scale.get_adjustment().get_upper()
        remaining = value - max_
        self._elapsed_label.set_time(value)
        self._remaining_label.set_time(remaining)
        self._remaining_label.set_disabled(not player.seekable)
        self._elapsed_label.set_disabled(not player.seekable)

        self.set_sensitive(player.seekable)


class SeekBarPlugin(EventPlugin):
    PLUGIN_ID = "SeekBar"
    PLUGIN_NAME = _("Alternative Seek Bar")
    PLUGIN_DESC = _(
        "Alternative seek bar which is always visible and spans "
        "the whole window width."
    )
    PLUGIN_ICON = Icons.GO_JUMP

    def enabled(self):
        self._bar = SeekBar(app.player, app.librarian)
        self._bar.show()
        app.window.set_seekbar_widget(self._bar)

    def disabled(self):
        app.window.set_seekbar_widget(None)
        del self._bar
