# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time
import gobject, gtk
from qltk.entry import ValidatingEntry
import config
import player

from plugins.events import EventPlugin

class Alarm(EventPlugin):
    PLUGIN_ID = "Alarm Clock"
    PLUGIN_NAME = _("Alarm Clock")
    PLUGIN_DESC = _("Wake you up with loud music.")
    PLUGIN_ICON = gtk.STOCK_DIALOG_INFO
    PLUGIN_VERSION = "0.22"

    _pref_name = "alarm_times"
    _times = ["HH:MM"] * 7
    _enabled = False

    def __init__(self):
        try: self._times = config.get("plugins", self._pref_name).split()[:7]
        except: pass
        else: self._times = (self._times + ["HH:MM"] * 7)[:7]
        gobject.timeout_add(30000, self._check)

    def enabled(self): self._enabled = True
    def disabled(self): self._enabled = False

    def is_valid_time(time):
        try: hour, minute = map(int, time.split(":"))
        except: return False
        else: return (hour < 24 and minute < 60)
    is_valid_time = staticmethod(is_valid_time)

    def plugin_on_song_started(self, song):
        pass

    def _entry_changed(self, entries):
        self._times = map(ValidatingEntry.get_text, entries)
        config.set("plugins", self._pref_name, " ".join(self._times))

    def _ready(self):
        tdata = time.localtime()
        goal = self._times[tdata.tm_wday]
        try: ghour, gminute = map(int, goal.split(":"))
        except: return False
        else: return (tdata.tm_hour, tdata.tm_min) == (ghour, gminute)

    def _fire(self):
        if self._enabled:
            if player.playlist.paused:
                if player.playlist.song is None:
                    player.playlist.next()
                else: player.playlist.paused = False
        gobject.timeout_add(60000, self._longer_check)

    def _longer_check(self):
        if self._ready(): self._fire()
        else: gobject.timeout_add(30000, self._check)

    def _check(self):
        if self._ready(): self._fire()
        else: return True

    def PluginPreferences(self, parent):
        t = gtk.Table(2, 7)
        t.set_col_spacings(6)
        entries = []
        for i in range(7):
            e = ValidatingEntry(Alarm.is_valid_time)
            e.set_text(self._times[i])
            e.set_max_length(5)
            e.set_width_chars(6)
            day = gtk.Label(
                time.strftime("_%A:", (2000, 1, 1, 0, 0, 0, i, 1, 0)))
            day.set_mnemonic_widget(e)
            day.set_use_underline(True)
            day.set_alignment(0.0, 0.5)
            t.attach(day, 0, 1, i, i + 1, xoptions=gtk.FILL)
            t.attach(e, 1, 2, i, i + 1, xoptions=gtk.FILL)
            entries.append(e)
        for e in entries:
            e.connect_object('changed', self._entry_changed, entries)
        return t

class Lullaby(Alarm):
    PLUGIN_ID = "Lullaby"
    PLUGIN_NAME = _("Lullaby")
    PLUGIN_DESC = _("Fade out and pause your music.")
    PLUGIN_ICON = gtk.STOCK_MEDIA_PAUSE
    PLUGIN_VERSION = "0.20"

    _pref_name = "lullaby_times"

    def _fire(self):
        if self._enabled:
            gobject.timeout_add(500, self._fade_out)
            self.__was_volume = player.playlist.volume
        else: gobject.timeout_add(30000, self._check)

    def _fade_out(self):
        player.playlist.volume -= 0.005
        if player.playlist.volume == 0:
            player.playlist.paused = True
        if player.playlist.paused:
            player.playlist.volume = self.__was_volume
            gobject.timeout_add(30000, self._check)
        else: return True
