# Copyright 2004-2006 Joe Wreschnig, Michael Urman, Iñigo Serna
#           2012 Christoph Reiter
#           2013,16,21 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from quodlibet import _
from quodlibet import app
from quodlibet.plugins import PluginNotSupportedError
from quodlibet.plugins.events import EventPlugin
from quodlibet.qltk import Icons
from quodlibet.util import is_osx

from .prefs import Preferences


if is_osx():
    # Works, but not without problems:
    # https://github.com/quodlibet/quodlibet/issues/1870
    # The dock menu is more useful so disable.
    raise PluginNotSupportedError

try:
    from .appindicator import AppIndicator
except ImportError as e:
    # AppIndicator3 is a GTK3 library, so this is currently always the case.
    # TODO GTK4: implement the StatusNotifierItem D-Bus spec directly.
    raise PluginNotSupportedError(str(e)) from e


class TrayIconPlugin(EventPlugin):
    PLUGIN_ID = "Tray Icon"
    PLUGIN_NAME = _("Tray Icon")
    PLUGIN_DESC = _("Controls Quod Libet from the system tray.")
    PLUGIN_ICON = Icons.USER_DESKTOP

    def enabled(self):
        self._tray = AppIndicator()
        self._tray.set_song(app.player.song)
        self._tray.set_info_song(app.player.info)
        self._tray.set_paused(app.player.paused)

    def disabled(self):
        self._tray.remove()
        del self._tray

    def PluginPreferences(self, parent):
        return Preferences()

    def plugin_on_song_started(self, song):
        self._tray.set_song(app.player.song)
        self._tray.set_info_song(app.player.info)

    def plugin_on_paused(self):
        self._tray.set_paused(True)

    def plugin_on_unpaused(self):
        self._tray.set_paused(False)
