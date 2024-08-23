# Copyright 2018 Phoenix Dailey
#           2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import random

from gi.repository import Gtk, GLib

from quodlibet import _
from quodlibet import app
from quodlibet.order import OrderInOrder
from quodlibet.order import OrderRemembered
from quodlibet.order.reorder import Reorder
from quodlibet.plugins import PluginConfig
from quodlibet.plugins.playorder import ShufflePlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.notif import Task


pconfig = PluginConfig("shufflebygrouping")
pconfig.defaults.set("grouping", "~grouping~album~albumartist")
pconfig.defaults.set("grouping_filter", "grouping")
pconfig.defaults.set("delay", 0)


class ShuffleByGrouping(ShufflePlugin, OrderRemembered):
    PLUGIN_ID = "Shuffle by Grouping"
    PLUGIN_NAME = _("Shuffle by Grouping")
    PLUGIN_DESC = _("Adds a shuffle mode that groups songs with a common tag "
                    "– similar to album shuffles.\n\n"
                    "This is useful for shuffling multi-movement classical "
                    "pieces, making sure all movements play in order "
                    "before shuffling to the next piece.")
    PLUGIN_ICON = Icons.MEDIA_PLAYLIST_SHUFFLE
    display_name = _("Shuffle by grouping")
    accelerated_name = _("Shuffle by _grouping")
    priority = Reorder.priority

    def next(self, playlist, current_song):
        return self._next(playlist, current_song)

    def _next(self, playlist, current_song, delay_on=True):
        grouping = str(pconfig.gettext("grouping")).strip()
        grouping_filter = str(pconfig.gettext("grouping_filter")).strip()
        delay = pconfig.getint("delay")

        def same_group(song_iter_a, song_iter_b):
            if song_iter_a is None or song_iter_b is None:
                return False
            song_a = playlist.get_value(song_iter_a)
            song_b = playlist.get_value(song_iter_b)
            if not self._tag_defined(grouping_filter, song_a):
                return False
            if not self._tag_defined(grouping_filter, song_b):
                return False
            return song_a(grouping) == song_b(grouping)

        # Keep track of played songs
        OrderRemembered.next(self, playlist, current_song)
        remaining = OrderRemembered.remaining(self, playlist)

        # Check if playlist is finished or empty
        if not remaining:
            OrderRemembered.reset(self, playlist)
            return None

        # Play next song in current grouping
        next_song = OrderInOrder.next(self, playlist, current_song)
        if same_group(next_song, current_song):
            return next_song

        # Pause for a moment before picking new group
        if delay_on:
            self._resume_after_delay(delay)

        # Pick random song at the start of a new group
        while True:
            song_location = random.choice(list(remaining.keys()))
            new_song = playlist.get_iter(song_location)
            new_song_prev = (playlist.get_iter(song_location - 1)
                             if song_location >= 1 else None)
            if not same_group(new_song, new_song_prev):
                return new_song

    @staticmethod
    def _resume_after_delay(delay, refresh_rate=20):
        if delay <= 0:
            return
        app.player.paused = True
        delay_timer = GLib.timeout_add(1000 * delay, app.player.play)
        task = Task(_("Shuffle by Grouping"),
                    _("Waiting to start new group…"),
                    stop=lambda: GLib.source_remove(delay_timer))

        def countdown():
            for i in range(int(refresh_rate * delay)):
                task.update(i / (refresh_rate * delay))
                yield True
            task.finish()
            yield False
        GLib.timeout_add(1000 / refresh_rate, next, countdown())

    @staticmethod
    def _tag_defined(tag_name, song):
        if not tag_name:
            return True
        tag_value = song(tag_name)
        return bool(tag_value.strip())

    def next_explicit(self, playlist, current_song):
        return self._next(playlist, current_song, delay_on=False)

    def previous(self, playlist, current_song):
        return OrderRemembered.previous(self, playlist, current_song)

    @classmethod
    def PluginPreferences(cls, window):
        def on_change(widget, config_entry):
            config_value = widget.get_text()
            pconfig.set(config_entry, config_value)

        def on_spin(widget, config_entry):
            config_value = widget.get_value()
            pconfig.set(config_entry, config_value)

        def default_on_click(widget):
            pconfig.reset("grouping")
            pconfig.reset("grouping_filter")
            pconfig.reset("delay")
            grouping_entry.set_text(pconfig.gettext("grouping"))
            grouping_filter_entry.set_text(pconfig.gettext("grouping_filter"))
            delay_spin.set_value(pconfig.getint("delay"))

        def make_label(label_text):
            label = Gtk.Label(label_text, selectable=True)
            label.set_alignment(0.0, 0.5)
            label.set_margin_end(3)
            return label

        vbox = Gtk.VBox(spacing=12)

        grouping_label = make_label(_("Grouping tag:"))
        grouping_entry = Gtk.Entry()
        grouping_entry.connect("changed", on_change, "grouping")
        grouping_entry.set_text(pconfig.gettext("grouping"))
        grouping_entry.set_tooltip_text(_("Tag to group songs by"))

        grouping_filter_label = make_label(_("Filter tag:"))
        grouping_filter_entry = Gtk.Entry()
        grouping_filter_entry.connect("changed", on_change, "grouping_filter")
        grouping_filter_entry.set_text(pconfig.gettext("grouping_filter"))
        grouping_filter_entry.set_tooltip_text(_(
            "Grouping is applied only if the filter tag is defined.\n"
            "A song with an undefined filter tag will be treated as\n"
            "a group consisting only of itself. Typically the filter\n"
            "tag should match or partially match the grouping tag."))

        delay_label = make_label(_("Delay:"))
        adj = Gtk.Adjustment.new(pconfig.getint("delay"), 0, 3600, 1, 5, 0)
        delay_spin = Gtk.SpinButton(adjustment=adj, climb_rate=0.1, digits=0)
        delay_spin.set_numeric(True)
        delay_spin.connect("value-changed", on_spin, "delay")
        delay_spin.set_tooltip_text(_(
            "Time delay in seconds before starting next group"))

        table = Gtk.Table(3, 2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        table.attach(grouping_label, 0, 1, 0, 1, Gtk.AttachOptions.FILL)
        table.attach(grouping_filter_label, 0, 1, 1, 2, Gtk.AttachOptions.FILL)
        table.attach(delay_label, 0, 1, 2, 3, Gtk.AttachOptions.FILL)

        table.attach(grouping_entry, 1, 2, 0, 1)
        table.attach(grouping_filter_entry, 1, 2, 1, 2)
        table.attach(delay_spin, 1, 2, 2, 3)

        vbox.add(table)

        defaults = Gtk.Button(_("Reset to defaults"))
        defaults.connect("clicked", default_on_click)
        vbox.add(defaults)

        return vbox
