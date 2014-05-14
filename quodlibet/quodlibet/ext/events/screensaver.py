# Copyright 2011 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import os

if os.name == "nt":
    from quodlibet.plugins import PluginNotSupportedError
    raise PluginNotSupportedError

from gi.repository import Gtk
import dbus

from quodlibet import app
from quodlibet.plugins.events import EventPlugin


class ScreensaverPause(EventPlugin):
    PLUGIN_ID = "screensaver_pause"
    PLUGIN_NAME = _("Screensaver Pause")
    PLUGIN_DESC = _("Pause while the GNOME screensaver is active.")
    PLUGIN_ICON = Gtk.STOCK_MEDIA_PAUSE
    PLUGIN_VERSION = "0.2"

    DBUS_NAME = "org.gnome.ScreenSaver"
    DBUS_INTERFACE = "org.gnome.ScreenSaver"
    DBUS_PATH = "/org/gnome/ScreenSaver"

    __was_paused = False
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
        elif not self.__was_paused:
            app.player.paused = False

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
