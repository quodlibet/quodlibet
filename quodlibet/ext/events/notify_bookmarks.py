# Copyright 2022 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from collections import deque

import gi

from quodlibet.formats import AudioFile
from quodlibet.player._base import BasePlayer
from quodlibet.qltk import Icons

try:
    gi.require_version("Notify", "0.7")
    from gi.repository import GLib, Notify
except (ValueError, ImportError) as e:
    from quodlibet import plugins
    raise plugins.PluginNotSupportedError(f"Can't load GI Notify module ({e!r})") from e


from quodlibet import app, _
from quodlibet.plugins import PluginConfigMixin
from quodlibet.plugins.events import EventPlugin
from quodlibet.util import format_time
from quodlibet.util.dprint import print_d


class BookmarkNotify(EventPlugin, PluginConfigMixin):
    PLUGIN_ID = "BookmarkNotify"
    PLUGIN_NAME = _("Bookmark Notifications")
    PLUGIN_DESC = _("Uses notifications to display bookmarks / comments in real-time. "
                    "Works well for the Soundcloud browser.")
    PLUGIN_ICON = Icons.DIALOG_INFORMATION

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._timer = None
        self.song: AudioFile | None = None
        self._bookmarks = []
        self._loaded = False

    def enabled(self) -> None:
        self._timer = GLib.timeout_add(1000, self._sync)

        if app.player:
            self._player: BasePlayer = app.player
        else:
            raise TypeError(f"App {app} has no player set up")

    def disabled(self) -> None:
        GLib.source_remove(self._timer)

    def _sync(self) -> bool:
        if not (self._player.paused):
            shown = 0
            while self.bookmarks:
                t, text = self.bookmarks[0]
                if t * 1000 < self._player.get_position():
                    if not shown:
                        # Limit throughput to 1 per tick (second currrently)
                        self._show(t, text)
                        shown += 1
                    self.bookmarks.popleft()
                else:
                    return True
        return True

    @property
    def bookmarks(self):
        if not self._bookmarks and not self._loaded and self.song:
            self._bookmarks = deque(self.song.bookmarks)
            if self._bookmarks:
                print_d(f"Loaded {len(self._bookmarks)} bookmarks")
                self._loaded = True
        return self._bookmarks

    @bookmarks.setter
    def bookmarks(self, bms):
        self._bookmarks = deque(bms)

    def _show(self, ts: int, line: str) -> None:
        if not self.song:
            return
        msg = f"♪ {format_time(ts)}: <b>{line.strip()}</b> ♪"
        print_d(msg)
        line = GLib.markup_escape_text(line)
        notif = Notify.Notification.new(f"Quodlibet – {self.song('title')}",
                                        f"<b>{line}</b> @ {format_time(ts)}",
                                        "user-idle")
        # notif.category = "im"
        notif.show()

    def plugin_on_song_started(self, song) -> None:
        self.song = song
        if self.song:
            Notify.init(f"Quodlibet - {self.song('title')}")
        self.bookmarks = []
        # Keep a track of whether we _ever_ got them for this song
        self._loaded = False

    def plugin_on_seek(self, song: AudioFile, msec: int) -> None:
        self.song = song
        self._reset_to(msec)

    def plugin_on_changed(self, songs):
        if self.song in songs:
            print_d("Song has been changed, reloading")
            self._loaded = False
            self.bookmarks = []

    def _reset_to(self, msec: int) -> None:
        print_d(f"Resetting to {format_time(msec / 1000)}")
        self.bookmarks = deque([] if self.song is None else self.song.bookmarks)
        while self.bookmarks:
            t, text = self.bookmarks[0]
            if t * 1000 < msec:
                self.bookmarks.popleft()
            else:
                time_str = format_time(msec / 1000)
                print_d(f"Next bookmark at {format_time(t)}s "
                        f"(at {time_str}) - {len(self.bookmarks)} left")
                return
        print_d("Finished bookmarks")
