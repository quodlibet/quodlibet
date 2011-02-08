# -*- coding: utf-8 -*-
# Copyright 2011 Nick Boultbee
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
from quodlibet import config
from quodlibet.plugins.playorder import PlayOrderPlugin, PlayOrderShuffleMixin


class TrackRepeatOrder(PlayOrderPlugin, PlayOrderShuffleMixin):
    PLUGIN_ID = "track_repeat"
    PLUGIN_NAME = _("Track Repeat")
    PLUGIN_ICON = "gtk-refresh"
    PLUGIN_VERSION = "0.1"
    PLUGIN_DESC = _("Shuffle songs, "
                    "but repeat every track a set number of times.")

    play_count = 0
    play_each = 2

    def __init__(self, playlist):
        super(TrackRepeatOrder, self).__init__(playlist)
        try:
            self.play_each = int(self.get_config("play_each"))
        except:
            config.set("plugins", "play_each", self.play_each)

    @classmethod
    def get_config(klass, name):
        key = __name__ + "_" + name
        return config.get("plugins", key)

    @classmethod
    def set_config(klass, name, value):
        key = __name__ + "_" + name
        config.set("plugins", key, value)

    @classmethod
    def PluginPreferences(klass, window):
        def plays_changed(spin):
            print_d("setting to %d" % int(spin.get_value()))
            klass.set_config("play_each", int(spin.get_value()))

        vb = gtk.VBox(spacing=10)
        vb.set_border_width(10)
        hbox = gtk.HBox(spacing=6)
        val = klass.get_config("play_each")
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
        print_d("Play count now at %d/%d" % (self.play_count, self.play_each),
                context=self)
        if (self.play_count < self.play_each and iter is not None):
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
        self.__play_count = 0
