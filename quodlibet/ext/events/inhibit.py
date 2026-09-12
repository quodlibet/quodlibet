# Copyright 2011 Christoph Reiter <reiter.christoph@gmail.com>
# Copyright 2020 Antigone <mail@antigone.xyz>
# Copyright 2026 Am-curious
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
from gi.repository import Gtk

from quodlibet import _
from quodlibet import app
from quodlibet import config
from quodlibet.qltk import Icons
from quodlibet.plugins.events import EventPlugin


def get_toplevel_xid():
    if app.window.get_window():
        try:
            return app.window.get_window().get_xid()
        except AttributeError:  # non x11
            pass
    return 0


class InhibitFlags:
    LOGOUT = 1
    USERSWITCH = 1 << 1
    SUSPEND = 1 << 2
    IDLE = 1 << 3


class InhibitStrings:
    SUSPEND = "inhibit_suspend"
    IDLE = "inhibit_idle"


class SessionInhibit(EventPlugin):
    PLUGIN_ID = "screensaver_inhibit"
    PLUGIN_NAME = _("Inhibit Screensaver/Suspend")
    PLUGIN_DESC = _(
        "When a song is playing, prevents either the screensaver from"
        " activating, or prevents the computer from suspending."
    )
    PLUGIN_ICON = Icons.PREFERENCES_DESKTOP_SCREENSAVER

    CONFIG_MODE = PLUGIN_ID + "_mode"

    GNOME_DBUS = (
        "org.gnome.SessionManager",
        "/org/gnome/SessionManager",
        "org.gnome.SessionManager",
    )
    FREEDESKTOP_DBUS = {
        InhibitStrings.IDLE: (
            "org.freedesktop.ScreenSaver",
            "/org/freedesktop/ScreenSaver",
            "org.freedesktop.ScreenSaver",
        ),
        InhibitStrings.SUSPEND: (
            "org.freedesktop.PowerManagement",
            "/org/freedesktop/PowerManagement/Inhibit",
            "org.freedesktop.PowerManagement.Inhibit",
        ),
    }

    APPLICATION_ID = "quodlibet"
    INHIBIT_REASON = _("Music is playing")

    __cookie = None
    __dbus_proxy = None
    __uninhibit_method = None

    def __get_dbus_proxy(self, dbus):
        name, path, interface = dbus
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        return Gio.DBusProxy.new_sync(
            bus,
            Gio.DBusProxyFlags.NONE,
            None,
            name,
            path,
            interface,
            None,
        )

    def enabled(self):
        if not app.player.paused:
            self.plugin_on_unpaused()

    def disabled(self):
        self.plugin_on_paused()

    def plugin_on_unpaused(self):
        if self.__cookie is not None:
            return

        xid = get_toplevel_xid()
        mode = config.get("plugins", self.CONFIG_MODE, InhibitStrings.IDLE)
        flags = (
            InhibitFlags.SUSPEND
            if mode == InhibitStrings.SUSPEND
            else InhibitFlags.IDLE
        )
        try:
            dbus_proxy = self.__get_dbus_proxy(self.GNOME_DBUS)
            cookie = dbus_proxy.Inhibit(
                "(susu)", self.APPLICATION_ID, xid, self.INHIBIT_REASON, flags
            )
            uninhibit_method = "Uninhibit"
        except GLib.Error:
            try:
                dbus_proxy = self.__get_dbus_proxy(self.FREEDESKTOP_DBUS[mode])
                cookie = dbus_proxy.Inhibit(
                    "(ss)", self.APPLICATION_ID, self.INHIBIT_REASON
                )
                uninhibit_method = "UnInhibit"
            except GLib.Error:
                return

        self.__dbus_proxy = dbus_proxy
        self.__cookie = cookie
        self.__uninhibit_method = uninhibit_method

    def plugin_on_paused(self):
        if self.__cookie is None:
            return

        dbus_proxy = self.__dbus_proxy
        cookie = self.__cookie
        uninhibit_method = self.__uninhibit_method
        self.__dbus_proxy = None
        self.__cookie = None
        self.__uninhibit_method = None

        try:
            getattr(dbus_proxy, uninhibit_method)("(u)", cookie)
        except GLib.Error:
            pass

    def PluginPreferences(self, parent):
        def changed(combo):
            index = combo.get_active()
            mode = InhibitStrings.SUSPEND if index == 1 else InhibitStrings.IDLE
            config.set("plugins", self.CONFIG_MODE, mode)
            if not app.player.paused:
                self.plugin_on_paused()
                self.plugin_on_unpaused()

        mode = config.get("plugins", self.CONFIG_MODE, InhibitStrings.IDLE)
        hb = Gtk.HBox(spacing=6)
        hb.set_border_width(6)
        # Translators: Inhibiting Mode
        hb.pack_start(Gtk.Label(label=_("Mode:")), False, True, 0)
        combo = Gtk.ComboBoxText()
        combo.append_text(_("Inhibit Screensaver"))
        combo.append_text(_("Inhibit Suspend"))
        combo.set_active(1 if mode == InhibitStrings.SUSPEND else 0)
        combo.connect("changed", changed)
        hb.pack_start(combo, True, True, 0)
        return hb
