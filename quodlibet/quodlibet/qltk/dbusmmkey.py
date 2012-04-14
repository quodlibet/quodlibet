# -*- coding: utf-8 -*-
# Copyright 2007 Ronny Haryanto <ronny at haryan.to>
#           2011,2012 Christoph Reiter <christoph.reiter@gmx.at>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

import time

import dbus
import gobject


class DBusMMKey(gobject.GObject):
    DBUS_NAME = "org.gnome.SettingsDaemon"

    # Work around the gnome-settings-daemon dbus interface
    # changing between 2.20 and 2.22 by connecting to both
    # the old and new object.
    DBUS_IFACES = [{"path": "/org/gnome/SettingsDaemon",
                   "interface": "org.gnome.SettingsDaemon"},
                  {"path": "/org/gnome/SettingsDaemon/MediaKeys",
                   "interface": "org.gnome.SettingsDaemon.MediaKeys"}]

    __gsignals__ = {
        'action': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,)),
        }

    @classmethod
    def is_active(cls):
        """If the gsd plugin is active atm"""
        bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
        # FIXME: check if the media-keys plugin is active
        return bus.name_has_owner(cls.DBUS_NAME)

    def __init__(self, window, name):
        super(DBusMMKey, self).__init__()
        self.__interface = None
        self.__watch = None
        self.__grab_time = -1
        self.__name = name
        self.__key_pressed_sig = None

        self.__grab()
        self.__enable_watch()
        self.__focus_sig = window.connect("notify::is-active",
                                          self.__focus_event)
        window.connect("destroy", self.__destroy)

    def __destroy(self, window):
        self.__disable_watch()
        self.__release()
        window.disconnect(self.__focus_sig)

    def __update_interface(self):
        """If __interface is None, set a proxy interface object and connect
        to the key pressed signal."""

        if self.__interface:
            return self.__interface

        bus = dbus.Bus(dbus.Bus.TYPE_SESSION)

        for desc in self.DBUS_IFACES:
            try:
                obj = bus.get_object(self.DBUS_NAME, desc["path"])
                iface = dbus.Interface(obj, desc["interface"])
                # try to call a method to test the interface
                iface.ReleaseMediaPlayerKeys(self.__name)
            except dbus.DBusException:
                pass
            else:
                self.__key_pressed_sig = iface.connect_to_signal(
                        "MediaPlayerKeyPressed", self.__key_pressed)
                self.__interface = iface
                break

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
            self.__grab(update=False)

    def __key_pressed(self, application, action):
        if application != self.__name:
            return

        self.emit("action", action)

    def __grab(self, update=True):
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

        try:
            iface.GrabMediaPlayerKeys(self.__name, self.__grab_time)
        except dbus.DBusException:
            pass

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

    def __focus_event(self, window, param):
        if window.get_property(param.name):
            self.__grab()
