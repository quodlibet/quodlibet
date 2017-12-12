# -*- coding: utf-8 -*-
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

import dbus

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

    def __screensaver_changed(self, active):
        # Gnome-Shell fires ActiveChanged even if it doesn't change
        # (aborted transition to lock screen), so handle that

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
            self.__sig.remove()
            self.__interface = None

    def __owner_changed(self, owner):
        if not owner:
            self.__remove_interface()
        elif not self.__interface:
            bus = dbus.SessionBus()
            obj = bus.get_object(self.DBUS_NAME, self.DBUS_PATH)
            iface = dbus.Interface(obj, self.DBUS_INTERFACE)
            self.__sig = iface.connect_to_signal("ActiveChanged",
                                                 self.__screensaver_changed)
            self.__active = iface.GetActive()
            self.__interface = iface

    def enabled(self):
        try:
            bus = dbus.SessionBus()
            self.__watch = bus.watch_name_owner(self.DBUS_NAME,
                                                self.__owner_changed)
        except dbus.DBusException:
            pass

    def disabled(self):
        if self.__watch:
            self.__watch.cancel()
        self.__remove_interface()
