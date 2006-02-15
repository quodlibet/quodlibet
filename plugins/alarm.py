# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import time
import gobject, gtk
from qltk.entry import ValidatingEntry
import config
import player

class Alarm(object):
    PLUGIN_NAME = "Alarm Clock"
    PLUGIN_DESC = "Wake you up with loud music."
    PLUGIN_ICON = gtk.STOCK_DIALOG_INFO
    PLUGIN_VERSION = "0.12"

    __times = ["HH:MM"] * 7

    def __init__(self):
        try: self.__times = config.get("plugins", "alarm_times").split()[:7]
        except: pass
        else: self.__times = (self.__times + ["HH:MM"] * 7)[:7]
        print "Alarms set for", self.__times
        gobject.timeout_add(30000, self.__check)

    def is_valid_time(time):
        try: hour, minute = map(int, time.split(":"))
        except: return False
        else: return (hour < 24 and minute < 60)
    is_valid_time = staticmethod(is_valid_time)

    def plugin_on_song_started(self, song):
        pass

    def __entry_changed(self, entries):
        self.__times = map(ValidatingEntry.get_text, entries)
        config.set("plugins", "alarm_times", " ".join(self.__times))

    def __ready(self):
        tdata = time.localtime()
        goal = self.__times[tdata.tm_wday]
        try: ghour, gminute = map(int, goal.split(":"))
        except: return False
        else: return (tdata.tm_hour, tdata.tm_min) == (ghour, gminute)

    def __fire(self):
        if getattr(self, "PMEnFlag", False):
            if player.playlist.paused:
                if player.playlist.song is None:
                    player.playlist.next()
                else: player.playlist.paused = False
        gobject.timeout_add(60000, self.__longer_check)

    def __longer_check(self):
        if self.__ready(): self.__fire()
        else: gobject.timeout_add(30000, self.__check)

    def __check(self):
        if self.__ready(): self.__fire()
        else: return True

    def PluginPreferences(self, parent):
        t = gtk.Table(2, 7)
        t.set_col_spacings(6)
        entries = []
        for i in range(7):
            e = ValidatingEntry(Alarm.is_valid_time)
            e.set_text(self.__times[i])
            e.set_max_length(5)
            e.set_width_chars(6)
            day = gtk.Label(time.strftime("_%A:", (0, 0, 0, 0, 0, 0, i, 0, 0)))
            day.set_mnemonic_widget(e)
            day.set_use_underline(True)
            day.set_alignment(0.0, 0.5)
            t.attach(day, 0, 1, i, i + 1, xoptions=gtk.FILL)
            t.attach(e, 1, 2, i, i + 1, xoptions=gtk.FILL)
            entries.append(e)
        for e in entries:
            e.connect_object('changed', self.__entry_changed, entries)
        return t
