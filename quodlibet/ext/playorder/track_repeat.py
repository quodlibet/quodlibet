# Copyright 2011-2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


from gi.repository import Gtk

from quodlibet import _
from quodlibet.order.repeat import Repeat
from quodlibet.plugins.playorder import RepeatPlugin
from quodlibet.util.dprint import print_d
from quodlibet.plugins import PluginConfigMixin
from quodlibet.qltk import Icons

START_COUNT = 1


class TrackRepeatOrder(RepeatPlugin, PluginConfigMixin):
    """ Repeats a given track a configurable number of times
        Useful for musicians practising / working out songs...
        or maybe you just REALLY like your playlist.
    """

    PLUGIN_ID = "track_repeat"
    PLUGIN_NAME = _("Repeat Each Track")
    PLUGIN_ICON = Icons.MEDIA_PLAYLIST_REPEAT
    PLUGIN_DESC = _("Adds a shuffle mode that plays tracks in order, "
                    "but repeating every track a set number of times.")
    PLAY_EACH_DEFAULT = 2

    START_COUNT = 1
    """By the time this plugin is invoked, the song has already been played"""

    # Plays of the current song
    play_count = START_COUNT
    priority = Repeat.priority

    @classmethod
    def PluginPreferences(cls, parent):
        def plays_changed(spin):
            cls.config_set("play_each", int(spin.get_value()))

        vb = Gtk.VBox(spacing=10)
        vb.set_border_width(10)
        hbox = Gtk.HBox(spacing=6)
        lbl = Gtk.Label(label=_("Number of times to play each song:"))
        hbox.pack_start(lbl, False, True, 0)
        val = cls.config_get("play_each", cls.PLAY_EACH_DEFAULT)
        spin = Gtk.SpinButton(
            adjustment=Gtk.Adjustment.new(float(val), 2, 20, 1, 10, 0))
        spin.connect("value-changed", plays_changed)
        hbox.pack_start(spin, False, True, 0)
        vb.pack_start(hbox, True, True, 0)
        vb.show_all()
        return vb

    def restart_counting(self):
        self.play_count = START_COUNT
        print_d("Resetting play count")

    def next(self, playlist, iter):
        play_each = int(self.config_get('play_each', self.PLAY_EACH_DEFAULT))
        self.play_count += 1
        if self.play_count <= play_each and iter is not None:
            print_d("Play count now at %d/%d" % (self.play_count, play_each))
            return iter
        else:
            self.restart_counting()
            return self.wrapped.next(playlist, iter)

    def next_explicit(self, playlist, iter):
        self.restart_counting()
        return self.wrapped.next_explicit(playlist, iter)

    def set(self, playlist, iter):
        self.restart_counting()
        return super().set(playlist, iter)

    def reset(self, playlist):
        self.play_count = 0
        return super().reset(playlist)
