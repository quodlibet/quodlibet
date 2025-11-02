# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk
from quodlibet import _, app
from quodlibet.plugins import PluginConfigMixin
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons
from quodlibet.qltk.tracker import TimeTracker


class ABRepeatEventPlugin(EventPlugin, PluginConfigMixin):
    PLUGIN_ID = "ABRepeat"
    PLUGIN_NAME = _("A-B Repeat")
    PLUGIN_ICON = Icons.GO_JUMP
    PLUGIN_CONFIG_SECTION = __name__
    PLUGIN_DESC = _("Repeats a section of a track defined by A and B timestamps.")

    def enabled(self):
        self._seekpoint_A, self._seekpoint_B = self._get_seekpoints()
        self._tracker = TimeTracker(app.player)
        self._tracker.connect("tick", self._on_tick)

    def disabled(self):
        self._tracker.destroy()

    def plugin_on_song_started(self, song):
        self._seekpoint_A, self._seekpoint_B = self._get_seekpoints()
        if self._seekpoint_A is not None:
            self._seek(self._seekpoint_A)

    def _on_tick(self, tracker):
        self._seekpoint_A, self._seekpoint_B = self._get_seekpoints()
        if self._seekpoint_A is None or self._seekpoint_B is None:
            return

        time = app.player.get_position() // 1000
        if self._seekpoint_B <= time:
            self._seek(self._seekpoint_A)

    def _get_seekpoints(self):
        if not app.player.song:
            return None, None

        seekpoint_a, seekpoint_b = app.player.get_ab_points()

        return seekpoint_a, seekpoint_b

    def _seek(self, seconds):
        app.player.seek(seconds * 1000)

    def PluginPreferences(self, parent):
        vb = Gtk.VBox(spacing=12)

        return vb
