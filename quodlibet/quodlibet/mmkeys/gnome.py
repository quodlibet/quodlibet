# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time

from gi.repository import GLib, Gio

from ._base import MMKeysBackend, MMKeysAction
from quodlibet.util.dbusutils import dbus_name_owned


class GnomeBackend(MMKeysBackend):

    DBUS_NAME = "org.gnome.SettingsDaemon.MediaKeys"
    DBUS_PATH = "/org/gnome/SettingsDaemon/MediaKeys"
    DBUS_IFACE = "org.gnome.SettingsDaemon.MediaKeys"

    _EVENTS = {
        "Next": MMKeysAction.NEXT,
        "Previous": MMKeysAction.PREV,
        "Play": MMKeysAction.PLAYPAUSE,
        "Pause": MMKeysAction.PAUSE,
        "Stop": MMKeysAction.STOP,
    }
    # TODO: Rewind, FastForward, Repeat, Shuffle

    def __init__(self, name, callback):
        self.__interface = None
        self.__watch = None
        self.__grab_time = -1
        self.__name = name
        self.__key_pressed_sig = None
        self.__callback = callback
        self.__enable_watch()

    @classmethod
    def is_active(cls):
        """If the gsd plugin is active atm"""
        return dbus_name_owned(cls.DBUS_NAME)

    def cancel(self):
        if self.__callback:
            self.__disable_watch()
            self.__release()
            self.__callback = None

    def grab(self, update=True):
        """Tells gsd that QL started or got the focus.
        update: whether to send the current time or the last one"""

        if update:
            # so this breaks every 50 days.. ok..
            self.__grab_time = int((time.time() * 1000)) & 0xFFFFFFFF
        elif self.__grab_time < 0:
            # can not send the last event if there was none
            return

        iface = self.__update_interface()
        if not iface:
            return

        try:
            iface.GrabMediaPlayerKeys('(su)', self.__name, self.__grab_time)
        except GLib.Error as e:
            if 'Error.ServiceUnknown' not in str(e):
                raise

    def __update_interface(self):
        """If __interface is None, set a proxy interface object and connect
        to the key pressed signal."""

        if self.__interface:
            return self.__interface

        try:
            iface = Gio.DBusProxy.new_for_bus_sync(
                Gio.BusType.SESSION, Gio.DBusProxyFlags.NONE, None,
                self.DBUS_NAME, self.DBUS_PATH, self.DBUS_IFACE, None)
        except GLib.Error:
            pass
        else:
            self.__key_pressed_sig = iface.connect(
                'g-signal', self.__on_signal)
            self.__interface = iface

        return self.__interface

    def __enable_watch(self):
        """Enable events for dbus name owner change"""
        if self.__watch:
            return

        # This also triggers for existing name owners
        self.__watch = Gio.bus_watch_name(
            Gio.BusType.SESSION, self.DBUS_NAME, Gio.BusNameWatcherFlags.NONE,
            self.__owner_appeared, self.__owner_vanished)

    def __disable_watch(self):
        """Disable name owner change events"""
        if self.__watch:
            Gio.bus_unwatch_name(self.__watch)
            self.__watch = None

    def __owner_appeared(self, bus, name, owner):
        """This gets called when the owner of the dbus name appears
        so we can handle gnome-settings-daemon restarts."""

        if not self.__interface:
            # new owner, get a new interface object and
            # resend the last grab event
            self.grab(update=False)

    def __owner_vanished(self, bus, owner):
        """This gets called when the owner of the dbus name disappears
        so we can handle gnome-settings-daemon restarts."""

        # owner gone, remove the signal matches/interface etc.
        self.__release()

    def __on_signal(self, proxy, sender, signal, args):
        if signal == 'MediaPlayerKeyPressed':
            application, action = args[:2]
            self.__key_pressed(application, action)

    def __key_pressed(self, application, action):
        if application != self.__name:
            return

        if action in self._EVENTS:
            self.__callback(self._EVENTS[action])

    def __release(self):
        """Tells gsd that we don't want events anymore and
        removes all signal matches"""

        if not self.__interface:
            return

        if self.__key_pressed_sig:
            self.__interface.disconnect(self.__key_pressed_sig)
            self.__key_pressed_sig = None

        try:
            self.__interface.ReleaseMediaPlayerKeys('(s)', self.__name)
        except GLib.Error:
            pass
        self.__interface = None


# https://mail.gnome.org/archives/desktop-devel-list/2017-April/msg00069.html
class GnomeBackendOldName(GnomeBackend):
    DBUS_NAME = "org.gnome.SettingsDaemon"


class MateBackend(GnomeBackend):

    DBUS_NAME = "org.mate.SettingsDaemon"
    DBUS_PATH = "/org/mate/SettingsDaemon/MediaKeys"
    DBUS_IFACE = "org.mate.SettingsDaemon.MediaKeys"
