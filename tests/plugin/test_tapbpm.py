# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from unittest.mock import Mock, patch

from gi.repository import Gdk, Gtk

from quodlibet.formats import AudioFile
from . import PluginTestCase


class TTapBpm(PluginTestCase):
    def setUp(self):
        self.panel = self.modules["Tap BPM"].TapBpmPanel(Mock(), AudioFile())

    def _controller(self, cls):
        controllers = self.panel.tap_btn.observe_controllers()
        return next(c for c in controllers if isinstance(c, cls))

    def test_clicking_tap_counts_a_tap(self):
        click = self._controller(Gtk.GestureClick)
        with patch.object(self.panel, "count_tap") as count_tap:
            click.emit("pressed", 1, 0, 0)
        count_tap.assert_called_once()

    def test_space_counts_a_tap_but_other_keys_do_not(self):
        key = self._controller(Gtk.EventControllerKey)
        with patch.object(self.panel, "count_tap") as count_tap:
            assert key.emit("key-pressed", Gdk.KEY_space, 0, 0)
            assert not key.emit("key-pressed", Gdk.KEY_a, 0, 0)
        count_tap.assert_called_once()
