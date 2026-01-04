# Synchronized Lyrics: a Quod Libet plugin for showing synchronized lyrics.
# Copyright (C) 2015 elfalem
#            2016-26 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
import functools
import re
from pathlib import Path

from gi.repository import Gtk, Gdk, GLib

from quodlibet import _, util
from quodlibet import app
from quodlibet import qltk
from quodlibet.formats import AudioFile
from quodlibet.plugins import PluginConfigMixin
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons
from quodlibet.util.dprint import print_d


class SynchronizedLyrics(EventPlugin, PluginConfigMixin):
    PLUGIN_ID = "SynchronizedLyrics"
    PLUGIN_NAME = _("Synchronized Lyrics")
    PLUGIN_DESC = _(
        "Shows synchronized lyrics from embedded lyrics, or a lyrics (lrc) file."
    )
    PLUGIN_ICON = Icons.FORMAT_JUSTIFY_FILL

    SYNC_PERIOD = 10000

    DEFAULT_BGCOLOR = "#343428282C2C"
    DEFAULT_TXTCOLOR = "#FFFFFFFFFFFF"
    DEFAULT_FONTSIZE = 25

    CFG_BGCOLOR_KEY = "backgroundColor"
    CFG_TXTCOLOR_KEY = "textColor"
    CFG_FONTSIZE_KEY = "fontSize"

    # Note the trimming of whitespace, seems "most correct" behaviour
    LINE_REGEX = re.compile(r"\s*\[([0-9]+:[0-9.]*)]\s*(.+)\s*")

    song: AudioFile | None

    def __init__(self) -> None:
        super().__init__()
        self.song = None
        self._lines: list[tuple[int, str]] = []
        self._timers: list[tuple[int, int]] = []
        self._start_clearing_from = 0
        self.textview = None
        self.scrolled_window = None

    def PluginPreferences(self, window):
        vb = Gtk.VBox(spacing=6)
        vb.set_border_width(6)

        t = Gtk.Table(n_rows=5, n_columns=2, homogeneous=True)
        t.set_col_spacings(6)
        t.set_row_spacings(3)

        clr_section = Gtk.Label()
        clr_section.set_markup(util.bold(_("Colors")))
        t.attach(clr_section, 0, 2, 0, 1)

        l = Gtk.Label(label=_("Text:"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 1, 2, xoptions=Gtk.AttachOptions.FILL)

        c = Gdk.RGBA()
        c.parse(self._get_text_color())
        b = Gtk.ColorButton(rgba=c)
        t.attach(b, 1, 2, 1, 2)
        b.connect("color-set", self._set_text_color)

        l = Gtk.Label(label=_("Background:"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 2, 3, xoptions=Gtk.AttachOptions.FILL)

        c = Gdk.RGBA()
        c.parse(self._get_background_color())
        b = Gtk.ColorButton(rgba=c)
        t.attach(b, 1, 2, 2, 3)
        b.connect("color-set", self._set_background_color)

        font_section = Gtk.Label()
        font_section.set_markup(util.bold(_("Font")))
        t.attach(font_section, 0, 2, 3, 4)

        l = Gtk.Label(label=_("Size (px):"))
        l.set_alignment(xalign=1.0, yalign=0.5)
        t.attach(l, 0, 1, 4, 5, xoptions=Gtk.AttachOptions.FILL)

        a = Gtk.Adjustment.new(self._get_font_size(), 10, 72, 2, 3, 0)
        s = Gtk.SpinButton(adjustment=a)
        s.set_numeric(True)
        s.set_text(str(self._get_font_size()))
        t.attach(s, 1, 2, 4, 5)
        s.connect("value-changed", self._set_font_size)

        vb.pack_start(t, False, False, 0)
        return vb

    @classmethod
    def _get_text_color(cls):
        v = cls.config_get(cls.CFG_TXTCOLOR_KEY, cls.DEFAULT_TXTCOLOR)
        return v[:3] + v[5:7] + v[9:11]

    @classmethod
    def _get_background_color(cls):
        v = cls.config_get(cls.CFG_BGCOLOR_KEY, cls.DEFAULT_BGCOLOR)
        return v[:3] + v[5:7] + v[9:11]

    @classmethod
    def _get_font_size(cls):
        return int(cls.config_get(cls.CFG_FONTSIZE_KEY, cls.DEFAULT_FONTSIZE))

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
        self.scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )
        self.scrolled_window.get_vadjustment().set_value(0)

        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textview.set_justification(Gtk.Justification.CENTER)
        self.scrolled_window.add_with_viewport(self.textview)

        vb = Gtk.HBox()
        vb.pack_start(self.scrolled_window, True, True, 6)
        vb.show_all()
        app.window.get_child().pack_start(vb, False, True, 0)
        app.window.get_child().reorder_child(vb, 2)

        self._style_lyrics_window()
        self.scrolled_window.show()

        self._sync_timer = GLib.timeout_add(self.SYNC_PERIOD, self._sync)
        self.song = app.player.song
        self._build_data(self.song, self._get_mtime())
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
        self.scrolled_window.set_size_request(-1, 1.5 * self._get_font_size())
        qltk.add_css(
            self.textview,
            f"""
            * {{
                background-color: {self._get_background_color()};
                color: {self._get_text_color()};
                font-size: {self._get_font_size()}px;
                padding: 0.25rem;
                border-radius: 6px;
            }}
        """,
        )

    def _cur_position(self):
        return app.player.get_position()

    @functools.lru_cache()  # noqa
    def _build_data(
        self, song: AudioFile | None, mtime: float = 0
    ) -> list[tuple[int, str]]:
        if not song:
            return []
        if lyrics := song("~lyrics"):
            print_d(f"Found embedded lyrics for {song.key}")
        else:
            path = song.lyrics_path
            if path is None:
                return []
            try:
                lyrics = path.read_text(encoding="utf-8")
                print_d(f"Found lyrics file: {path}")
            except FileNotFoundError:
                print_d(f"No lyrics found for {path}")
                return []
        return self._parse_lrc(lyrics)

    def _parse_lrc(self, contents: str) -> list[tuple[int, str]]:
        data = []
        for line in contents.splitlines():
            match = self.LINE_REGEX.match(line)
            if not match:
                continue
            timing, text = match.groups()
            minutes, seconds = (float(p) for p in timing.split(":", 1))
            timestamp = int(1000 * (minutes * 60 + seconds))
            data.append((timestamp, text))
        return sorted(data)

    def _set_timers(self):
        if not self._timers:
            cur_time = self._cur_position()
            cur_idx = self._greater(self._lines, cur_time)
            if cur_idx != -1:
                while (
                    cur_idx < len(self._lines)
                    and self._lines[cur_idx][0] < cur_time + self.SYNC_PERIOD
                ):
                    timestamp = self._lines[cur_idx][0]
                    line = self._lines[cur_idx][1]
                    tid = GLib.timeout_add(timestamp - cur_time, self._show, line)
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
        for _ts, tid in self._timers[self._start_clearing_from :]:
            GLib.source_remove(tid)
        self._timers = []
        self._start_clearing_from = 0

    def _show(self, line) -> bool:
        if self.textview:
            self.textview.get_buffer().set_text(line)
        self._start_clearing_from += 1
        print_d(f"♪ {line.strip()} ♪")
        return False

    def plugin_on_song_started(self, song: AudioFile) -> None:
        self.song = song
        self._clear_timers()
        self._lines = self._build_data(song, self._get_mtime())
        self._clear_view()
        # delay so that current position is for current track, not previous one
        GLib.timeout_add(2, self._timer_control)

    def _clear_view(self):
        if self.textview:
            self.textview.get_buffer().set_text("")

    def _get_mtime(self) -> float:
        if not self.song:
            return 0
        path = self.song.lyrics_path
        if path is None:
            return 0
        if not path.exists():
            path = Path(str(self.song.key))
        if not path.exists():
            return 0
        return path.stat().st_mtime

    def plugin_on_song_ended(self, song, stopped):
        self._clear_timers()

    def plugin_on_paused(self):
        self._timer_control()

    def plugin_on_unpaused(self):
        self._timer_control()

    def plugin_on_seek(self, song, msec):
        if not app.player.paused:
            self._clear_view()
            self._clear_timers()
            self._set_timers()

    def plugin_on_changed(self, songs):
        if self.song in songs:
            print_d("Current song changed, updating lyrics")
            self._lines = self._build_data(self.song, self._get_mtime())
            self._clear_timers()
            self._set_timers()

    def _greater(self, array, probe):
        length = len(array)
        if length == 0:
            return -1
        if probe < array[0][0]:
            return 0
        if probe >= array[length - 1][0]:
            return length
        return self._search(array, probe, 0, length - 1)

    def _search(self, array, probe, lower, upper):
        if lower == upper:
            if array[lower][0] <= probe:
                return lower + 1
            return lower
        middle = int((lower + upper) / 2)
        if array[middle][0] <= probe:
            return self._search(array, probe, middle + 1, upper)
        return self._search(array, probe, lower, middle)
