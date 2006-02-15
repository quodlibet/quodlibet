# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import time
import gobject, gtk
import player

class ClockPlug(object):
    def __clicked(self, cb, hb):
        self._enabled = cb.get_active()
        hb.set_sensitive(self._enabled)

    def __set_time(self, entry):
        t = entry.get_text()
        try: hour, minute = map(int, t.split(":"))
        except: self._starttime = -1
        else: self._starttime = hour * 60 + minute

    def PluginPreferences(self, parent):
        hb = gtk.HBox(spacing=6)
        hb.set_border_width(6)
        e = gtk.Entry()
        if self._starttime == -1: e.set_text("Enter a time in HH:MM format.")
        else: e.set_text("%d:%02d" % (
            self._starttime / 60, self._starttime % 60))
        e.connect('changed', self.__set_time)
        cb = gtk.CheckButton(self.message)
        cb.set_active(self._enabled)
        e.set_sensitive(self._enabled)
        cb.connect('clicked', self.__clicked, e)
        hb.pack_start(cb, expand=False)
        hb.pack_start(e, expand=True)
        hb.show_all()
        return hb

class Lullaby(ClockPlug):
    PLUGIN_NAME = "Lullaby"
    PLUGIN_DESC = "Turn off your music after you go to sleep."
    PLUGIN_ICON = gtk.STOCK_MEDIA_PAUSE
    PLUGIN_VERSION = "0.11"

    message = "Turn off at:"

    def __init__(self):
        self._starttime = -1
        self._enabled = False

    def plugin_on_song_ended(self, song, stopped):
        if self._enabled and not stopped:
            time_ = time.localtime()[3] * 60 + time.localtime()[4]
            if (self._starttime > 0 and self._starttime < time_ and
                (time_ - self._starttime < 30)):
                self._enabled = False
                player.playlist.paused = True
