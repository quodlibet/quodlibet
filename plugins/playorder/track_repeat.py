# -*- coding: utf-8 -*-
# Copyright 2011,2012 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# Repeats a given track a configurable number of times
# Useful for musicians practising / working out songs...
# or maybe you just REALLY like your playlist.
#
# TODO: notification of play count? Non-shuffle? Integration with main UI?
#

import gtk
from quodlibet.plugins.playorder import PlayOrderPlugin, PlayOrderShuffleMixin
from quodlibet.util.dprint import print_d
from quodlibet.plugins import PluginConfigMixin


class TrackRepeatOrder(PlayOrderPlugin,
        PlayOrderShuffleMixin, PluginConfigMixin):
    PLUGIN_ID = "track_repeat"
    PLUGIN_NAME = _("Track Repeat")
    PLUGIN_ICON = "gtk-refresh"
    PLUGIN_VERSION = "0.2"
    PLUGIN_DESC = _("Shuffle songs, "
                    "but repeat every track a set number of times.")
    PLAY_EACH_DEFAULT = 2

    # Plays of the current song
    play_count = 0

    @classmethod
    def PluginPreferences(cls):
        def plays_changed(spin):
            cls.config_set("play_each", int(spin.get_value()))

        vb = gtk.VBox(spacing=10)
        vb.set_border_width(10)
        hbox = gtk.HBox(spacing=6)
        val = cls.config_get("play_each", cls.PLAY_EACH_DEFAULT)
        spin = gtk.SpinButton(gtk.Adjustment(float(val), 2, 20, 1, 10))
        spin.connect("value-changed", plays_changed)
        hbox.pack_start(spin, expand=False)
        lbl = gtk.Label(_("Number of times to play each song"))
        hbox.pack_start(lbl, expand=False)
        vb.pack_start(hbox, expand=True)
        vb.show_all()
        return vb

    def restart_counting(self):
        self.play_count = 0
        print_d("Resetting play count", context=self)

    def next(self, playlist, iter):
        self.play_count += 1
        play_each = int(self.config_get('play_each', self.PLAY_EACH_DEFAULT))
        print_d("Play count now at %d/%d" % (self.play_count, play_each))
        if self.play_count < play_each and iter is not None:
            return iter
        else:
            self.restart_counting()
            return super(TrackRepeatOrder, self).next(playlist, iter)

    def next_explicit(self, *args):
        self.restart_counting()
        return super(TrackRepeatOrder, self).next(*args)

    def previous(self, *args):
        return super(TrackRepeatOrder, self).previous(*args)

    def set(self, playlist, iter):
        self.restart_counting()
        return super(TrackRepeatOrder, self).set(playlist, iter)

    def reset(self, playlist):
        super(TrackRepeatOrder, self).reset(playlist)
        self.play_count = 0
