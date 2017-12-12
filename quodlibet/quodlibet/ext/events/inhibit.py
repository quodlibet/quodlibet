# -*- coding: utf-8 -*-
# Copyright 2011 Christoph Reiter <reiter.christoph@gmail.com>
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


def get_toplevel_xid():
    if app.window.get_window():
        try:
            return app.window.get_window().get_xid()
        except AttributeError:  # non x11
            pass
    return 0


class InhibitFlags(object):
    LOGOUT = 1
    USERSWITCH = 1 << 1
    SUSPEND = 1 << 2
    IDLE = 1 << 3


class SessionInhibit(EventPlugin):
    PLUGIN_ID = "screensaver_inhibit"
    PLUGIN_NAME = _("Inhibit Screensaver")
    PLUGIN_DESC = _("Prevents the GNOME screensaver from activating while"
                    " a song is playing.")
    PLUGIN_ICON = Icons.PREFERENCES_DESKTOP_SCREENSAVER

    DBUS_NAME = "org.gnome.SessionManager"
    DBUS_INTERFACE = "org.gnome.SessionManager"
    DBUS_PATH = "/org/gnome/SessionManager"

    APPLICATION_ID = "quodlibet"
    INHIBIT_REASON = _("Music is playing")

    __cookie = None

    def enabled(self):
        if not app.player.paused:
            self.plugin_on_unpaused()

    def disabled(self):
        if not app.player.paused:
            self.plugin_on_paused()

    def plugin_on_unpaused(self):
        xid = dbus.UInt32(get_toplevel_xid())
        flags = dbus.UInt32(InhibitFlags.IDLE)

        try:
            bus = dbus.SessionBus()
            obj = bus.get_object(self.DBUS_NAME, self.DBUS_PATH)
            iface = dbus.Interface(obj, self.DBUS_INTERFACE)
            self.__cookie = iface.Inhibit(
                self.APPLICATION_ID, xid, self.INHIBIT_REASON, flags)
        except dbus.DBusException:
            pass

    def plugin_on_paused(self):
        if self.__cookie is None:
            return

        try:
            bus = dbus.SessionBus()
            obj = bus.get_object(self.DBUS_NAME, self.DBUS_PATH)
            iface = dbus.Interface(obj, self.DBUS_INTERFACE)
            iface.Uninhibit(self.__cookie)
            self.__cookie = None
        except dbus.DBusException:
            pass
