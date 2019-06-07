# -*- coding: utf-8 -*-
# Synchronized Lyrics: a Quod Libet plugin for showing synchronized lyrics.
# Copyright (C) 2015 elfalem
#            2016-17 Nick Boultbee
# Modified to support mp3 tags and ELRC syntax by Tomás Ralph
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
from quodlibet.util.songwrapper import SongWrapper


class SynchronizedLyrics(EventPlugin, PluginConfigMixin):

    PLUGIN_ID = 'SynchronizedLyrics'
    PLUGIN_NAME = _('Synchronized Lyrics')
    PLUGIN_DESC = _('Shows synchronized lyrics from .lrc file with same name \
as the track or embedded lyrics.')
    PLUGIN_ICON = Icons.FORMAT_JUSTIFY_FILL

    SYNC_PERIOD = 10000

    DEFAULT_BGCOLOR = '#343428282C2C'
    DEFAULT_TXTCOLOR = '#FFFFFFFFFFFF'
    DEFAULT_HIGHLIGHT = '#F222FDDD1BBB'
    DEFAULT_FONTSIZE = 25

    CFG_BGCOLOR_KEY = "backgroundColor"
    CFG_TXTCOLOR_KEY = "textColor"
    CFG_HIGHLIGHT_KEY = "highlightColor"
    CFG_FONTSIZE_KEY = "fontSize"

    _lines = []
    _words = []
    _timers = []

    _current_lrc = ""
    _start_clearing_from = 0
    textview = None
    scrolled_window = None

    highlight_position = 0

    foundELRC = False
    del foundELRC

    raw_file_check = None

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

        l = Gtk.Label(label=_("Highlight (Needs restart)"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 3, 4, xoptions=Gtk.AttachOptions.FILL)

        c = Gdk.RGBA()
        c.parse(cls._get_highlight_color())
        b = Gtk.ColorButton(rgba=c)
        t.attach(b, 1, 2, 3, 4)
        b.connect('color-set', cls._set_highlight_color)

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
        t.attach(font_section, 0, 2, 5, 6)

        l = Gtk.Label(label=_("Size (px):"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 6, 7, xoptions=Gtk.AttachOptions.FILL)

        a = Gtk.Adjustment.new(cls._get_font_size(), 10, 72, 2, 3, 0)
        s = Gtk.SpinButton(adjustment=a)
        s.set_numeric(True)
        s.set_text(str(cls._get_font_size()))
        t.attach(s, 1, 2, 6, 7)
        s.connect('value-changed', cls._set_font_size)

        vb.pack_start(t, False, False, 0)
        return vb

    def _get_text_color(self):
        v = self.config_get(self.CFG_TXTCOLOR_KEY, self.DEFAULT_TXTCOLOR)
        return v[:3] + v[5:7] + v[9:11]

    def _get_highlight_color(self):
        v = self.config_get(self.CFG_HIGHLIGHT_KEY, self.DEFAULT_HIGHLIGHT)
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

    def _set_highlight_color(self, button):
        self.config_set(self.CFG_HIGHLIGHT_KEY,
            button.get_color().to_string())
        self._highlight_text()

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
        self.adjustment = self.scrolled_window.get_vadjustment()

        app.window.get_child().pack_start(self.scrolled_window,
            False, True, 0)
        app.window.get_child().reorder_child(self.scrolled_window, 2)

        self._style_lyrics_window()

        self.adjustment.set_value(0)

        self.scrolled_window.show()

        self._sync_timer = GLib.timeout_add(self.SYNC_PERIOD, self._sync)
        self._build_data()
        self._timer_control()
        cur = app.player.info
        if cur is not None:
            cur = SongWrapper(cur)

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

    def _highlight_text(self):
        return self._get_highlight_color()

    def _cur_position(self):
        return app.player.get_position()

    def _build_data(self):
        cur = app.player.info
        if cur is not None:
            cur = SongWrapper(cur)
        self.text_buffer.set_text("")
        if app.player.song is not None:
            # check in same location as track
            track_name = app.player.song.get("~filename")
            new_lrc = os.path.splitext(track_name)[0] + ".lrc"
            print_d("Checking for lyrics tag")
            if self._current_lrc != new_lrc:
                self._lines = []
                self._words = []
                if os.path.exists(new_lrc):
                    print_d("Found lyrics file")
                    self._parse_lrc_file(new_lrc, "file")
                else:
                    new_lrc = cur("~lyrics")
                    print_d("Couldn't find lyrics file, defaulting to tags")
                    self._parse_lrc_file(new_lrc, "tag")
            self._current_lrc = new_lrc

    def _parse_lrc_file(self, lyrics, tagOrFile):
        if tagOrFile == "file":
            with open(lyrics, 'r', encoding="utf-8") as f:
                raw_file = f.read()
            self.raw_file_check = raw_file
        elif tagOrFile == "tag":
            raw_file = lyrics
            raw_file.encode(encoding="utf-8")
            self.raw_file_check = raw_file
        raw_file = raw_file.replace("\n", "")
        begin = 0
        beginELRC = 0
        keep_reading = len(raw_file) != 0
        tmp_dict = {}
        tmp_word_dict = {}
        compressed = []
        compressedWords = []
        bracketType = 0
        goToNextLine = True
        wentToNextLine = False
        while keep_reading:
            if goToNextLine:
                next_line = raw_file.find("[", begin + 1)
                wentToNextLine = True
            goToNextLine = False

            start_ELRC = raw_file.find("[", beginELRC, next_line)
            bracketType = 0
            if start_ELRC == -1:
                start_ELRC = raw_file.find("<", beginELRC, next_line)
                bracketType = 1
            next_ELRC = raw_file.find("<", start_ELRC + 1, next_line)

            if next_ELRC == -1:
                next_ELRC = next_line
                goToNextLine = True

            if next_line == -1:
                start_ELRC = raw_file.find("[", beginELRC)
                bracketType = 0
                if start_ELRC == -1:
                    start_ELRC = raw_file.find("<", beginELRC)
                    bracketType = 1
                next_ELRC = raw_file.find("<", start_ELRC + 1)
                word = raw_file[start_ELRC:next_ELRC]
                if next_ELRC == -1:
                    keep_reading = False
                    word = raw_file[start_ELRC:]
            else:
                word = raw_file[start_ELRC:next_ELRC]

            begin = next_line
            beginELRC = next_ELRC

            # parse lyricsLine
            if len(word) < 2 or not word[1].isdigit():
                continue
            if bracketType == 0:
                close_bracket = word.find("]")
                line = raw_file[start_ELRC:next_line]
            if bracketType == 1:
                close_bracket = word.find(">")
            t = datetime.strptime(word[1:close_bracket], '%M:%S.%f')
            timestamp = (t.minute * 60000 + t.second * 1000 +
                         t.microsecond / 1000)
            if wentToNextLine:
                wentToNextLine = False
                stripELRC = True
                newLineToStrip = line[close_bracket + 1:]
                currentStrip = newLineToStrip
                beginStrip = 0
                while stripELRC:
                    startStrippingELRC = newLineToStrip.find("<", beginStrip)
                    endStrippingELRC = newLineToStrip.find(">",
                        beginStrip + 1)
                    strippedLine = currentStrip.replace(
                    newLineToStrip[startStrippingELRC:endStrippingELRC + 1],
                        "")
                    currentStrip = strippedLine
                    beginStrip = endStrippingELRC
                    if startStrippingELRC and endStrippingELRC == -1:
                        stripELRC = False
                        thisLine = strippedLine
            words = word[close_bracket + 1:]
            if not words:
                compressedWords.append(timestamp)
            else:
                tmp_word_dict[timestamp] = words
                for t in compressedWords:
                    tmp_word_dict[t] = words
                compressedWords = []
            if not thisLine:
                compressed.append(timestamp)
            else:
                tmp_dict[timestamp] = thisLine
                for t in compressed:
                    tmp_dict[t] = thisLine
                compressed = []

        keys = list(tmp_dict.keys())
        wordKey = list(tmp_word_dict.keys())
        keys.sort()
        wordKey.sort()
        for key in keys:
            self._lines.append((key, tmp_dict[key]))
        for key in wordKey:
            self._words.append((key, tmp_word_dict[key]))
        del keys
        del tmp_dict
        del wordKey
        del tmp_word_dict

    def _set_timers(self):
        print_d("Setting timers")
        if len(self._timers) == 0:
            if self.raw_file_check.find("<") != -1:
                self.foundELRC = True
            if self.foundELRC:
                cur_time = self._cur_position()
                cur_idx = self._greater(self._words, cur_time)
                if cur_idx != -1:
                    cur_lin_idx = cur_idx
                    while (cur_idx < len(self._words)
                        and self._words[cur_idx][0] < cur_time +
                        self.SYNC_PERIOD):
                        timestamp = self._words[cur_idx][0]
                        line = self._lines[cur_lin_idx][1]
                        word = self._words[cur_idx][1]
                        if cur_lin_idx < len(self._lines) - 1:
                            if self._lines[cur_lin_idx + 1][0] == timestamp:
                                cur_lin_idx += 1
                                line = self._lines[cur_lin_idx][1]
                        if timestamp - cur_time > 0:
                            tid = GLib.timeout_add(timestamp - cur_time,
                                self._show_ELRC, line, word)
                        self._timers.append((timestamp, tid))
                        cur_idx += 1
            else:
                cur_time = self._cur_position()
                cur_idx = self._greater(self._lines, cur_time)
                if cur_idx != -1:
                    while (cur_idx < len(self._lines)
                        and self._lines[cur_idx][0] < cur_time +
                        self.SYNC_PERIOD):
                        timestamp = self._lines[cur_idx][0]
                        line = self._lines[cur_idx][1]
                        tid = GLib.timeout_add(timestamp - cur_time,
                            self._show, line)
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

    def _show_ELRC(self, line, word):
        startOfLineCurrent = self.text_buffer.get_start_iter()
        endOfLineCurrent = self.text_buffer.get_end_iter()
        current = self.text_buffer.get_text(startOfLineCurrent,
            endOfLineCurrent, True)
        self.text_buffer.set_text(line)
        startOfLine = self.text_buffer.get_start_iter()
        endOfLine = self.text_buffer.get_end_iter()
        modified = self.text_buffer.get_text(startOfLine, endOfLine, True)
        if modified != current:
            self.highlight_position = 0
        self.highlight_position += len(word)
        startIter = self.text_buffer.get_iter_at_offset(0)
        endIter = self.text_buffer.get_iter_at_offset(self.highlight_position)
        self.text_buffer.create_tag("highlight",
            foreground=self._highlight_text())
        self.text_buffer.apply_tag_by_name("highlight", startIter, endIter)
        print_d("♪ %s ♪" % line.strip())
        self._start_clearing_from += 1
        return False

    def _show(self, line):
        self.text_buffer.set_text(line)
        self._start_clearing_from += 1
        print_d("♪ %s ♪" % line.strip())
        return False

    def plugin_on_song_started(self, song):
        self.foundELRC = False
        self._build_data()
        #delay so that current position is for current track, not previous one
        GLib.timeout_add(1, self._timer_control)

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
