# Copyright 2011,2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys

if os.name == "nt" or sys.platform == "darwin":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

from gi.repository import Gio
from gi.repository import GLib

from quodlibet import _
from quodlibet import app
from quodlibet.qltk import Icons
from quodlibet.plugins.events import EventPlugin


class ScreensaverPause(EventPlugin):
    PLUGIN_ID = "screensaver_pause"
    PLUGIN_NAME = _("Screensaver Pause")
    PLUGIN_DESC = _("Pauses playback while the GNOME screensaver is active.")
    PLUGIN_ICON = Icons.MEDIA_PLAYBACK_PAUSE

    DBUS_NAME = "org.gnome.ScreenSaver"
    DBUS_INTERFACE = "org.gnome.ScreenSaver"
    DBUS_PATH = "/org/gnome/ScreenSaver"

    __was_paused = False
    __ignore_next = False
    __interface = None
    __active = False
    __watch = None

    def __on_signal(self, proxy, sender, signal, args):
        if signal == 'ActiveChanged':
            # Gnome-Shell fires ActiveChanged even if it doesn't change
            # (aborted transition to lock screen), so handle that
            active = args[0]
            if active == self.__active:
                return
            self.__active = active

            if active:
                self.__was_paused = app.player.paused
                app.player.paused = True
            elif not self.__was_paused and not self.__ignore_next:
                app.player.paused = False

            self.__ignore_next = False

    def plugin_on_unpaused(self):
        # In case pause/unpause happens while the session is inactive
        # (mpris, remote, etc.) don't unpause when it gets active again
        self.__ignore_next = True

    plugin_on_paused = plugin_on_unpaused

    def __remove_interface(self):
        if self.__interface:
            self.__interface.disconnect(self.__sig)
            self.__interface = None

    def __owner_appeared(self, bus, name, owner):
        if not self.__interface:
            iface = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, None,
                self.DBUS_NAME, self.DBUS_PATH, self.DBUS_INTERFACE, None)
            self.__sig = iface.connect('g-signal', self.__on_signal)
            self.__active = iface.GetActive()
            self.__interface = iface

    def __owner_vanished(self, bus, owner):
        self.__remove_interface()

    def enabled(self):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            self.__watch = Gio.bus_watch_name_on_connection(
                bus, self.DBUS_NAME, Gio.BusNameWatcherFlags.NONE,
                self.__owner_appeared, self.__owner_vanished)
        except GLib.Error:
            pass

    def disabled(self):
        if self.__watch:
            Gio.bus_unwatch_name(self.__watch)
        self.__remove_interface()
