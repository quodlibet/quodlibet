# -*- coding: utf-8 -*-
# Synchronized Lyrics: a Quod Libet plugin for showing synchronized lyrics.
# Copyright (C) 2015 elfalem
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.


"""Provides `Synchronized Lyrics` plugin for showing synchronized lyrics."""

import os

from datetime import datetime

from gi.repository import Gtk, Gdk, GLib

from quodlibet import app
from quodlibet import qltk
from quodlibet import config

from quodlibet.plugins.events import EventPlugin


class SynchronizedLyrics(EventPlugin):

    PLUGIN_ID = 'SynchronizedLyrics'
    PLUGIN_NAME = _('Synchronized Lyrics')
    PLUGIN_DESC = _('Shows synchronized lyrics from .lrc file with same name \
as the track.')

    SYNC_PERIOD = 3000

    _defaultBgColor = '#343428282C2C'
    _defaultTxtColor = '#FFFFFFFFFFFF'
    _defaultFontSize = 25

    _lines = []
    _timers = []

    _currentLrc = ""

    def PluginPreferences(self, window):
        vb = Gtk.VBox(spacing=6)
        vb.set_border_width(6)

        t = Gtk.Table(n_rows=5, n_columns=2, homogeneous=True)
        t.set_col_spacings(6)
        t.set_row_spacings(3)

        clrSection = Gtk.Label()
        clrSection.set_markup("<b>" + _("Colors") + "</b>")
        t.attach(clrSection, 0, 2, 0, 1)

        l = Gtk.Label(label=_("Text:"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL)

        c = Gdk.RGBA()
        c.parse(self.getTextColor())
        b = Gtk.ColorButton(rgba=c)
        t.attach(b, 1, 2, 1, 2)
        b.connect('color-set', self.setTextColor)

        l = Gtk.Label(label=_("Background:"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 2, 3, xoptions=Gtk.AttachOptions.FILL)

        c = Gdk.RGBA()
        c.parse(self.getBgColor())
        b = Gtk.ColorButton(rgba=c)
        t.attach(b, 1, 2, 2, 3)
        b.connect('color-set', self.setBgColor)

        fontSection = Gtk.Label()
        fontSection.set_markup("<b>" + _("Font") + "</b>")
        t.attach(fontSection, 0, 2, 3, 4)

        l = Gtk.Label(label=_("Size (px):"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 4, 5, xoptions=Gtk.AttachOptions.FILL)

        a = Gtk.Adjustment.new(self.getFontSize(), 6, 36, 1, 3, 0)
        s = Gtk.SpinButton(adjustment=a)
        s.set_numeric(True)
        s.set_text(str(self.getFontSize()))
        t.attach(s, 1, 2, 4, 5)
        s.connect('value-changed', self.setFontSize)

        vb.pack_start(t, False, False, 0)
        return vb

    def getTextColor(self):
        v = config.get("plugins", self.PLUGIN_ID + "_txt",
                       self._defaultTxtColor)
        return v[:3] + v[5:7] + v[9:11]

    def getBgColor(self):
        v = config.get("plugins", self.PLUGIN_ID + "_bg", self._defaultBgColor)
        return v[:3] + v[5:7] + v[9:11]

    def getFontSize(self):
        return int(config.get("plugins", self.PLUGIN_ID + "_fsize",
                              self._defaultFontSize))

    def setTextColor(self, button):
        config.set("plugins", self.PLUGIN_ID + "_txt",
                   button.get_color().to_string())
        self.styleLyricsWindow()

    def setBgColor(self, button):
        config.set("plugins", self.PLUGIN_ID + "_bg",
                   button.get_color().to_string())
        self.styleLyricsWindow()

    def setFontSize(self, sButton):
        config.set("plugins", self.PLUGIN_ID + "_fsize",
                   sButton.get_value_as_int())
        self.styleLyricsWindow()

    def enabled(self):
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                        Gtk.PolicyType.AUTOMATIC)
        self.adjustment = self.scrolled_window.get_vadjustment()

        self.textview = Gtk.TextView()
        self.textbuffer = self.textview.get_buffer()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_justification(Gtk.Justification.CENTER)
        self.scrolled_window.add_with_viewport(self.textview)
        self.textview.show()

        app.window.get_child().pack_start(self.scrolled_window, False, True, 0)
        app.window.get_child().reorder_child(self.scrolled_window, 2)

        self.textview.set_name("syncLyricsWindow")
        self.styleLyricsWindow()

        self.adjustment.set_value(0)

        self.scrolled_window.show()

        self._syncTimer = GLib.timeout_add(self.SYNC_PERIOD, self._sync)
        self.buildData()
        self.timerControl()

    def styleLyricsWindow(self):
        qltk.add_css(self.textview, """
            #syncLyricsWindow {{
                background-color: {0};
                color: {1};
                font-size: {2}px;
                font-weight: bold;
            }}
        """.format(self.getBgColor(), self.getTextColor(), self.getFontSize()))

    def curPosition(self):
        return app.player.get_position()

    def disabled(self):
        self.clearTimers()
        GLib.source_remove(self._syncTimer)
        self.textview.destroy()
        self.scrolled_window.destroy()

    def buildData(self):
        self.textbuffer.set_text("")
        if app.player.song is not None:
            #check in same location as track
            trackName = app.player.song.get("~filename")
            newLrc = os.path.splitext(trackName)[0] + ".lrc"
            if self._currentLrc != newLrc:
                self._lines = []
                if os.path.exists(newLrc):
                    self.parseLrcFile(newLrc)
            self._currentLrc = newLrc

    def parseLrcFile(self, filename):
        rawFile = ""
        with open(filename, 'r') as lrcfile:
            rawFile = lrcfile.read()

        rawFile = rawFile.replace("\n", "")
        begin = 0
        keepReading = len(rawFile) != 0
        tmp_dict = {}
        compressed = []
        while keepReading:
            lyricsLine = ""
            nextFind = rawFile.find("[", begin + 1)
            if(nextFind == -1):
                keepReading = False
                lyricsLine = rawFile[begin:]
            else:
                lyricsLine = rawFile[begin:nextFind]
            begin = nextFind

            #parse lyricsLine
            if not lyricsLine[1].isdigit():
                continue
            closeBracket = lyricsLine.find("]")
            timeObject = datetime.strptime(lyricsLine[1:closeBracket],
                                           '%M:%S.%f')
            timeStamp = (timeObject.minute * 60000 + timeObject.second * 1000
                         + timeObject.microsecond / 1000)
            words = lyricsLine[closeBracket + 1:]
            if words == "":
                compressed.append(timeStamp)
            else:
                tmp_dict[timeStamp] = words
                for t in compressed:
                    tmp_dict[t] = words
                compressed = []

        keys = tmp_dict.keys()
        keys.sort()
        for key in keys:
            self._lines.append((key, tmp_dict[key]))
        del keys
        del tmp_dict

    def setTimers(self):
        if len(self._timers) == 0:
            curTime = self.curPosition()
            curIndex = self.greater(self._lines, curTime)
            if curIndex != -1:
                while (curIndex < len(self._lines) and
                       self._lines[curIndex][0] < curTime + self.SYNC_PERIOD):

                    timeStamp = self._lines[curIndex][0]
                    lyricsLine = self._lines[curIndex][1]
                    timerId = GLib.timeout_add(timeStamp - curTime, self._show,
                                               lyricsLine)
                    self._timers.append((timeStamp, timerId))
                    curIndex += 1

    def _sync(self):
        if not app.player.paused:
            self.clearTimers()
            self.setTimers()
        return True

    def timerControl(self):
        if app.player.paused:
            self.clearTimers()
        else:
            self.setTimers()
        return False

    def clearTimers(self):
        curIndex = 0
        while curIndex < len(self._timers):
            GLib.source_remove(self._timers[curIndex][1])
            curIndex += 1
        self._timers = []

    def plugin_on_song_started(self, song):
        self.buildData()
        #delay so that current position is for current track, not previous one
        GLib.timeout_add(5, self.timerControl)

    def plugin_on_song_ended(self, song, stopped):
        self.clearTimers()

    def plugin_on_paused(self):
        self.timerControl()

    def _show(self, line):
        self.textbuffer.set_text(line)
        return False

    def plugin_on_unpaused(self):
        self.timerControl()

    def plugin_on_seek(self, song, msec):
        if not app.player.paused:
            self.clearTimers()
            self.setTimers()

    def greater(self, array, probe):
        length = len(array)
        if length == 0:
            return -1
        elif probe < array[0][0]:
            return 0
        elif probe >= array[length - 1][0]:
            return length
        else:
            return self.search(array, probe, 0, length - 1)

    def search(self, array, probe, lower, upper):
        if lower == upper:
            if array[lower][0] <= probe:
                return lower + 1
            else:
                return lower
        else:
            middle = int((lower + upper) / 2)
            if array[middle][0] <= probe:
                return self.search(array, probe, middle + 1, upper)
            else:
                return self.search(array, probe, lower, middle)
