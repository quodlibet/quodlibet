# -*- coding: utf-8 -*-
# Copyright 2014 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import time

from ._base import MMKeysBackend, MMKeysAction, MMKeysImportError

try:
    import dbus
except ImportError:
    raise MMKeysImportError


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
        try:
            bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
            return bus.name_has_owner(cls.DBUS_NAME)
        except dbus.DBusException:
            return False

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
            t = int((time.time() * 1000)) & 0xFFFFFFFF
            self.__grab_time = dbus.UInt32(t)
        elif self.__grab_time < 0:
            # can not send the last event if there was none
            return

        iface = self.__update_interface()
        if not iface:
            return

        iface.GrabMediaPlayerKeys(self.__name, self.__grab_time,
                                  reply_handler=lambda *x: None,
                                  error_handler=lambda *x: None)

    def __update_interface(self):
        """If __interface is None, set a proxy interface object and connect
        to the key pressed signal."""

        if self.__interface:
            return self.__interface

        try:
            bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
            obj = bus.get_object(self.DBUS_NAME, self.DBUS_PATH)
            iface = dbus.Interface(obj, self.DBUS_IFACE)
        except dbus.DBusException:
            pass
        else:
            self.__key_pressed_sig = iface.connect_to_signal(
                    "MediaPlayerKeyPressed", self.__key_pressed)
            self.__interface = iface

        return self.__interface

    def __enable_watch(self):
        """Enable events for dbus name owner change"""
        if self.__watch:
            return

        bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
        # This also triggers for existing name owners
        self.__watch = bus.watch_name_owner(self.DBUS_NAME,
                                            self.__owner_changed)

    def __disable_watch(self):
        """Disable name owner change events"""
        if self.__watch:
            self.__watch.cancel()
            self.__watch = None

    def __owner_changed(self, owner):
        """This gets called when the owner of the dbus name changes so we can
        handle gnome-settings-daemon restarts."""

        if not owner:
            # owner gone, remove the signal matches/interface etc.
            self.__release()
        elif not self.__interface:
            # new owner, get a new interface object and
            # resend the last grab event
            self.grab(update=False)

    def __key_pressed(self, application, action):
        if application != self.__name:
            return

        if action in self._EVENTS:
            self.__callback(self._EVENTS[action])

    def __release(self):
        """Tells gsd that we don't want events anymore and
        removes all signal matches"""

        if self.__key_pressed_sig:
            self.__key_pressed_sig.remove()
            self.__key_pressed_sig = None

        if self.__interface:
            try:
                self.__interface.ReleaseMediaPlayerKeys(self.__name)
            except dbus.DBusException:
                pass
            self.__interface = None


# https://mail.gnome.org/archives/desktop-devel-list/2017-April/msg00069.html
class GnomeBackendOldName(GnomeBackend):
    DBUS_NAME = "org.gnome.SettingsDaemon"


class MateBackend(GnomeBackend):

    DBUS_NAME = "org.mate.SettingsDaemon"
    DBUS_PATH = "/org/mate/SettingsDaemon/MediaKeys"
    DBUS_IFACE = "org.mate.SettingsDaemon.MediaKeys"
