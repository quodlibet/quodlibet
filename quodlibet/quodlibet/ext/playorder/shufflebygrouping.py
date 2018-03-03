# -*- coding: utf-8 -*-
# Copyright 2018 Phoenix Dailey
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


pconfig = PluginConfig("shufflebygrouping")
pconfig.defaults.set("grouping", "~grouping~album~albumartist")
pconfig.defaults.set("grouping_test", "grouping")
pconfig.defaults.set("delay", 0)


class ShuffleByGrouping(ShufflePlugin, OrderInOrder, OrderRemembered):
    PLUGIN_ID = "shufflebygrouping"
    PLUGIN_NAME = _("Shuffle by Grouping")
    PLUGIN_DESC = _("Shuffles by a grouping of songs defined by a common tag "
                    "instead of by track, similar to album shuffle. This is "
                    "useful for shuffling multi-movement classical works "
                    "while making sure all movements play in order before "
                    "shuffling to the next piece.")
    PLUGIN_ICON = Icons.MEDIA_PLAYLIST_SHUFFLE
    display_name = _("Shuffle by grouping")
    priority = Reorder.priority

    def next(self, playlist, current):
        return self._next(playlist, current)

    def _next(self, playlist, current, delay_on=True):
        grouping = str(pconfig.gettext("grouping")).strip()
        grouping_test = str(pconfig.gettext("grouping_test")).strip()
        delay = pconfig.getint("delay")

        # Keep track of played songs
        OrderRemembered.next(self, playlist, current)
        remaining = OrderRemembered.remaining(self, playlist)

        # Check if playlist is finished or empty
        if len(remaining) <= 0:
            OrderRemembered.reset(self, playlist)
            return None

        # Play next song in current grouping
        next_song = super().next(playlist, current)
        if (current is not None and next_song is not None and
            self._tag_defined(grouping_test, playlist, next_song) and
            self._same_tag(grouping, playlist, current, next_song)):
            return next_song

        # Pause for a moment before picking new group
        if delay_on and delay > 0:
            app.player.paused = True
            GLib.timeout_add(1000 * delay, app.player.play)

        # Pick random song at the start of a new group
        while True:
            song_location = random.choice(list(remaining.keys()))
            new_song = playlist.get_iter(song_location)

            if song_location <= 0:
                break
            if not self._tag_defined(grouping_test, playlist, new_song):
                break
            new_song_prev = playlist.get_iter(song_location - 1)
            if not self._same_tag(grouping, playlist, new_song, new_song_prev):
                break

        return new_song

    @staticmethod
    def _tag_defined(tag_name, playlist, song_iter):
        if tag_name == "":
            return True
        song = playlist.get_value(song_iter)
        tag_value = song(tag_name)
        if tag_value.strip() != "":
            return True
        return False

    @staticmethod
    def _same_tag(tag, playlist, song_iter_a, song_iter_b):
        song_a = playlist.get_value(song_iter_a)
        song_b = playlist.get_value(song_iter_b)
        if song_a(tag) == song_b(tag):
            return True
        return False

    def next_explicit(self, playlist, current):
        return self._next(playlist, current, delay_on=False)

    def previous(self, playlist, current):
        return OrderRemembered.previous(self, playlist, current)

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
            pconfig.reset("grouping_test")
            pconfig.reset("delay")
            grouping_entry.set_text(pconfig.gettext("grouping"))
            grouping_test_entry.set_text(pconfig.gettext("grouping_test"))
            delay_spin.set_value(pconfig.getint("delay"))

        vbox = Gtk.VBox(spacing=12)
        vbox.set_border_width(0)

        grouping_label = Gtk.Label(_("Grouping tag:"))
        grouping_label.set_alignment(0.0, 0.5)
        grouping_label.set_margin_end(3)
        grouping_entry = Gtk.Entry()
        grouping_entry.connect('changed', on_change, "grouping")
        grouping_entry.set_text(pconfig.gettext("grouping"))
        grouping_entry.set_tooltip_text(_("Tag to group songs by"))

        grouping_test_label = Gtk.Label(_("Test tag:"))
        grouping_test_label.set_alignment(0.0, 0.5)
        grouping_test_label.set_margin_end(3)
        grouping_test_entry = Gtk.Entry()
        grouping_test_entry.connect('changed', on_change, "grouping_test")
        grouping_test_entry.set_text(pconfig.gettext("grouping_test"))
        grouping_test_entry.set_tooltip_text(_(
            "Grouping is applied only if the test tag is defined.\n"
            "A song with an undefined test tag will be treated as\n"
            "a group consisting only of itself."))

        delay_label = Gtk.Label(_("Delay:"))
        delay_label.set_alignment(0.0, 0.5)
        delay_label.set_margin_end(3)
        adj = Gtk.Adjustment.new(pconfig.getint("delay"), 0, 3600, 1, 5, 0)
        delay_spin = Gtk.SpinButton(adjustment=adj, climb_rate=0.1, digits=0)
        delay_spin.set_numeric(True)
        delay_spin.connect('value-changed', on_spin, "delay")
        delay_spin.set_tooltip_text(_(
            "Time delay in seconds before starting next group"))

        table = Gtk.Table(3, 2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        table.attach(grouping_label, 0, 1, 0, 1, Gtk.AttachOptions.FILL)
        table.attach(grouping_test_label, 0, 1, 1, 2, Gtk.AttachOptions.FILL)
        table.attach(delay_label, 0, 1, 2, 3, Gtk.AttachOptions.FILL)

        table.attach(grouping_entry, 1, 2, 0, 1)
        table.attach(grouping_test_entry, 1, 2, 1, 2)
        table.attach(delay_spin, 1, 2, 2, 3)

        vbox.add(table)

        defaults = Gtk.Button(_("Reset to defaults"))
        defaults.connect('clicked', default_on_click)
        vbox.add(defaults)

        vbox.show_all()
        return vbox
