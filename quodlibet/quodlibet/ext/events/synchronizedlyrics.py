# -*- coding: utf-8 -*-
# Synchronized Lyrics: a Quod Libet plugin for showing synchronized lyrics.
# Copyright (C) 2015 elfalem
#            2016-17 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.


"""Provides `Synchronized Lyrics` plugin for showing synchronized lyrics."""

import os

from datetime import datetime

from gi.repository import Gtk, Gdk, GLib

from quodlibet.qltk import Icons
from quodlibet.util.dprint import print_d

from quodlibet import _
from quodlibet import app
from quodlibet import qltk

from quodlibet.plugins import PluginConfigMixin

from quodlibet.plugins.events import EventPlugin


class SynchronizedLyrics(EventPlugin, PluginConfigMixin):

    PLUGIN_ID = 'SynchronizedLyrics'
    PLUGIN_NAME = _('Synchronized Lyrics')
    PLUGIN_DESC = _('Shows synchronized lyrics from .lrc file with same name \
as the track.')
    PLUGIN_ICON = Icons.FORMAT_JUSTIFY_FILL

    SYNC_PERIOD = 10000

    DEFAULT_BGCOLOR = '#343428282C2C'
    DEFAULT_TXTCOLOR = '#FFFFFFFFFFFF'
    DEFAULT_FONTSIZE = 25

    CFG_BGCOLOR_KEY = "backgroundColor"
    CFG_TXTCOLOR_KEY = "textColor"
    CFG_FONTSIZE_KEY = "fontSize"

    _lines = []
    _timers = []

    _current_lrc = ""
    _start_clearing_from = 0
    textview = None
    scrolled_window = None

    def PluginPreferences(cls, window):
        vb = Gtk.VBox(spacing=6)
        vb.set_border_width(6)

        t = Gtk.Table(n_rows=5, n_columns=2, homogeneous=True)
        t.set_col_spacings(6)
        t.set_row_spacings(3)

        clr_section = Gtk.Label()
        clr_section.set_markup("<b>" + _("Colors") + "</b>")
        t.attach(clr_section, 0, 2, 0, 1)

        l = Gtk.Label(label=_("Text:"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL)

        c = Gdk.RGBA()
        c.parse(cls._get_text_color())
        b = Gtk.ColorButton(rgba=c)
        t.attach(b, 1, 2, 1, 2)
        b.connect('color-set', cls._set_text_color)

        l = Gtk.Label(label=_("Background:"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 2, 3, xoptions=Gtk.AttachOptions.FILL)

        c = Gdk.RGBA()
        c.parse(cls._get_background_color())
        b = Gtk.ColorButton(rgba=c)
        t.attach(b, 1, 2, 2, 3)
        b.connect('color-set', cls._set_background_color)

        font_section = Gtk.Label()
        font_section.set_markup("<b>" + _("Font") + "</b>")
        t.attach(font_section, 0, 2, 3, 4)

        l = Gtk.Label(label=_("Size (px):"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 4, 5, xoptions=Gtk.AttachOptions.FILL)

        a = Gtk.Adjustment.new(cls._get_font_size(), 10, 72, 2, 3, 0)
        s = Gtk.SpinButton(adjustment=a)
        s.set_numeric(True)
        s.set_text(str(cls._get_font_size()))
        t.attach(s, 1, 2, 4, 5)
        s.connect('value-changed', cls._set_font_size)

        vb.pack_start(t, False, False, 0)
        return vb

    def _get_text_color(self):
        v = self.config_get(self.CFG_TXTCOLOR_KEY, self.DEFAULT_TXTCOLOR)
        return v[:3] + v[5:7] + v[9:11]

    def _get_background_color(self):
        v = self.config_get(self.CFG_BGCOLOR_KEY, self.DEFAULT_BGCOLOR)
        return v[:3] + v[5:7] + v[9:11]

    def _get_font_size(self):
        return int(self.config_get(self.CFG_FONTSIZE_KEY,
                                   self.DEFAULT_FONTSIZE))

    def _set_text_color(self, button):
        self.config_set(self.CFG_TXTCOLOR_KEY, button.get_color().to_string())
        self._style_lyrics_window()

    def _set_background_color(self, button):
        self.config_set(self.CFG_BGCOLOR_KEY, button.get_color().to_string())
        self._style_lyrics_window()

    def _set_font_size(self, button):
        self.config_set(self.CFG_FONTSIZE_KEY, button.get_value_as_int())
        self._style_lyrics_window()

    def enabled(self):
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                        Gtk.PolicyType.AUTOMATIC)
        self.adjustment = self.scrolled_window.get_vadjustment()

        self.textview = Gtk.TextView()
        self.text_buffer = self.textview.get_buffer()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_justification(Gtk.Justification.CENTER)
        self.scrolled_window.add_with_viewport(self.textview)

        self.textview.show()

        app.window.get_child().pack_start(self.scrolled_window, False, True, 0)
        app.window.get_child().reorder_child(self.scrolled_window, 2)

        self._style_lyrics_window()

        self.adjustment.set_value(0)

        self.scrolled_window.show()

        self._sync_timer = GLib.timeout_add(self.SYNC_PERIOD, self._sync)
        self._build_data()
        self._timer_control()

    def disabled(self):
        self._clear_timers()
        GLib.source_remove(self._sync_timer)
        self.textview.destroy()
        self.textview = None
        self.scrolled_window.destroy()
        self.scrolled_window = None

    def _style_lyrics_window(self):
        if self.scrolled_window is None:
            return
        self.scrolled_window.set_size_request(-1, 1.6 * self._get_font_size())
        qltk.add_css(self.textview, """
            * {{
                background-color: {0};
                color: {1};
                font-size: {2}px;
                padding: 0.2em;
            }}
        """.format(self._get_background_color(), self._get_text_color(),
                   self._get_font_size()))

    def _cur_position(self):
        return app.player.get_position()

    def _build_data(self):
        self.text_buffer.set_text("")
        if app.player.song is not None:
            # check in same location as track
            track_name = app.player.song.get("~filename")
            new_lrc = os.path.splitext(track_name)[0] + ".lrc"
            print_d("Checking for lyrics file %s" % new_lrc)
            if self._current_lrc != new_lrc:
                self._lines = []
                if os.path.exists(new_lrc):
                    print_d("Found lyrics file: %s" % new_lrc)
                    self._parse_lrc_file(new_lrc)
            self._current_lrc = new_lrc

    def _parse_lrc_file(self, filename):
        with open(filename, 'r', encoding="utf-8") as f:
            raw_file = f.read()
        raw_file = raw_file.replace("\n", "")
        begin = 0
        keep_reading = len(raw_file) != 0
        tmp_dict = {}
        compressed = []
        while keep_reading:
            next_find = raw_file.find("[", begin + 1)
            if next_find == -1:
                keep_reading = False
                line = raw_file[begin:]
            else:
                line = raw_file[begin:next_find]
            begin = next_find

            # parse lyricsLine
            if len(line) < 2 or not line[1].isdigit():
                continue
            close_bracket = line.find("]")
            t = datetime.strptime(line[1:close_bracket], '%M:%S.%f')
            timestamp = (t.minute * 60000 + t.second * 1000 +
                         t.microsecond / 1000)
            words = line[close_bracket + 1:]
            if not words:
                compressed.append(timestamp)
            else:
                tmp_dict[timestamp] = words
                for t in compressed:
                    tmp_dict[t] = words
                compressed = []

        keys = list(tmp_dict.keys())
        keys.sort()
        for key in keys:
            self._lines.append((key, tmp_dict[key]))
        del keys
        del tmp_dict

    def _set_timers(self):
        print_d("Setting timers")
        if len(self._timers) == 0:
            cur_time = self._cur_position()
            cur_idx = self._greater(self._lines, cur_time)
            if cur_idx != -1:
                while (cur_idx < len(self._lines) and
                       self._lines[cur_idx][0] < cur_time + self.SYNC_PERIOD):

                    timestamp = self._lines[cur_idx][0]
                    line = self._lines[cur_idx][1]
                    tid = GLib.timeout_add(timestamp - cur_time, self._show,
                                           line)
                    self._timers.append((timestamp, tid))
                    cur_idx += 1

    def _sync(self):
        if not app.player.paused:
            self._clear_timers()
            self._set_timers()
        return True

    def _timer_control(self):
        if app.player.paused:
            self._clear_timers()
        else:
            self._set_timers()
        return False

    def _clear_timers(self):
        for ts, tid in self._timers[self._start_clearing_from:]:
            GLib.source_remove(tid)
        self._timers = []
        self._start_clearing_from = 0

    def _show(self, line):
        self.text_buffer.set_text(line)
        self._start_clearing_from += 1
        print_d("♪ %s ♪" % line.strip())
        return False

    def plugin_on_song_started(self, song):
        self._build_data()
        # delay so that current position is for current track, not previous one
        GLib.timeout_add(5, self._timer_control)

    def plugin_on_song_ended(self, song, stopped):
        self._clear_timers()

    def plugin_on_paused(self):
        self._timer_control()

    def plugin_on_unpaused(self):
        self._timer_control()

    def plugin_on_seek(self, song, msec):
        if not app.player.paused:
            self._clear_timers()
            self._set_timers()

    def _greater(self, array, probe):
        length = len(array)
        if length == 0:
            return -1
        elif probe < array[0][0]:
            return 0
        elif probe >= array[length - 1][0]:
            return length
        else:
            return self._search(array, probe, 0, length - 1)

    def _search(self, array, probe, lower, upper):
        if lower == upper:
            if array[lower][0] <= probe:
                return lower + 1
            else:
                return lower
        else:
            middle = int((lower + upper) / 2)
            if array[middle][0] <= probe:
                return self._search(array, probe, middle + 1, upper)
            else:
                return self._search(array, probe, lower, middle)
