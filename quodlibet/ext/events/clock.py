# Copyright 2006 Joe Wreschnig
#        2016,18 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time

from gi.repository import Gtk, GLib

from quodlibet import _
from quodlibet import app
from quodlibet import config
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk.entry import ValidatingEntry
from quodlibet.qltk import Icons
from quodlibet.util import connect_obj


class Alarm(EventPlugin):
    PLUGIN_ID = "Alarm Clock"
    PLUGIN_NAME = _("Alarm Clock")
    PLUGIN_DESC = _("Wakes you up with loud music.")
    PLUGIN_ICON = Icons.APPOINTMENT_NEW

    _pref_name = "alarm_times"
    _times = ["HH:MM"] * 7
    _enabled = False

    def __init__(self):
        try:
            self._times = config.get("plugins", self._pref_name).split(" ")[:7]
        except Exception:
            pass
        else:
            self._times = (self._times + ["HH:MM"] * 7)[:7]
        GLib.timeout_add(30000, self._check)

    def enabled(self):
        self._enabled = True

    def disabled(self):
        self._enabled = False

    @staticmethod
    def is_valid_time(time):
        try:
            hour, minute = map(int, time.split(":"))
        except Exception:
            return False
        else:
            return hour < 24 and minute < 60

    def plugin_on_song_started(self, song):
        pass

    def _entry_changed(self, entries):
        self._times = [ValidatingEntry.get_text(e) for e in entries]
        config.set("plugins", self._pref_name, " ".join(self._times))

    def _ready(self):
        tdata = time.localtime()
        goal = self._times[tdata.tm_wday]
        try:
            ghour, gminute = map(int, goal.split(":"))
        except Exception:
            return False
        else:
            return (tdata.tm_hour, tdata.tm_min) == (ghour, gminute)

    def _fire(self):
        if self._enabled:
            if app.player.paused:
                if app.player.song is None:
                    app.player.next()
                else:
                    app.player.paused = False
        GLib.timeout_add(60000, self._longer_check)

    def _longer_check(self):
        if self._ready():
            self._fire()
        else:
            GLib.timeout_add(30000, self._check)

    def _check(self):
        if self._ready():
            self._fire()
            return None
        return True

    def PluginPreferences(self, parent):
        t = Gtk.Table(n_rows=2, n_columns=7)
        t.set_col_spacings(6)
        entries = []
        for i in range(7):
            e = ValidatingEntry(Alarm.is_valid_time)
            e.set_size_request(100, -1)
            e.set_text(self._times[i])
            e.set_max_length(5)
            e.set_width_chars(6)
            day = Gtk.Label(label=time.strftime("_%A:", (2000, 1, 1, 0, 0, 0, i, 1, 0)))
            day.set_mnemonic_widget(e)
            day.set_use_underline(True)
            day.set_alignment(0.0, 0.5)
            t.attach(day, 0, 1, i, i + 1, xoptions=Gtk.AttachOptions.FILL)
            t.attach(e, 1, 2, i, i + 1, xoptions=Gtk.AttachOptions.FILL)
            entries.append(e)
        for e in entries:
            connect_obj(e, "changed", self._entry_changed, entries)
        return t


class Lullaby(Alarm):
    PLUGIN_ID = "Lullaby"
    PLUGIN_NAME = _("Lullaby")
    PLUGIN_DESC = _("Fades out and pauses your music.")
    PLUGIN_ICON = Icons.MEDIA_PLAYBACK_PAUSE

    _pref_name = "lullaby_times"

    def _fire(self):
        if self._enabled:
            GLib.timeout_add(500, self._fade_out)
            self.__was_volume = app.player.volume
        else:
            GLib.timeout_add(30000, self._check)

    def _fade_out(self):
        app.player.volume -= 0.005
        if app.player.volume == 0:
            app.player.paused = True
        if app.player.paused:
            app.player.volume = self.__was_volume
            GLib.timeout_add(30000, self._check)
        else:
            return True
        return None
