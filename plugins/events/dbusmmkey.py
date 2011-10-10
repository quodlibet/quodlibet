# -*- coding: utf-8 -*-
# Copyright 2007 Ronny Haryanto <ronny at haryan.to>
#           2011 Christoph Reiter <christoph.reiter@gmx.at>
#
# Thank you to Joe Wreschnig for the hints and Facundo Batista
# for the initial patch to quodlibet.py.
#
# This plugin is needed for quod libet to handle multimedia keys properly in
# GNOME 2.18. gnome-settings-daemon grabs all keys and publish it as dbus
# signals, thus preventing applications like quod libet to grab the key
# directly. When this plugin is enabled quod libet will use whichever
# method is currently available. For more info and background to the story,
# see: https://bugs.launchpad.net/ubuntu/+source/quodlibet/+bug/43464
#
# ------------------------------------------------------------------------
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import time

import dbus

from quodlibet import widgets
from quodlibet.plugins.events import EventPlugin

def get_bus():
    try:
        return dbus.Bus(dbus.Bus.TYPE_SESSION)
    except dbus.DBusException, err:
        print_w("[dbusmmkey] %s", err)

class DBusMMKey(EventPlugin):
    PLUGIN_ID = "DBusMMKey"
    PLUGIN_NAME = _("DBus Multimedia Keys")
    PLUGIN_DESC = _("Enable DBus-based Multimedia Shortcut Keys")
    PLUGIN_VERSION = "0.3"

    DBUS_NAME = "org.gnome.SettingsDaemon"

    # Work around the gnome-settings-daemon dbus interface
    # changing between 2.20 and 2.22 by connecting to both
    # the old and new object.
    DBUS_IFACES = [{"path": "/org/gnome/SettingsDaemon",
                   "interface": "org.gnome.SettingsDaemon"},
                  {"path": "/org/gnome/SettingsDaemon/MediaKeys",
                   "interface": "org.gnome.SettingsDaemon.MediaKeys"}]

    APP_NAME = "quodlibet"

    __interface = None
    __watch = None
    __grab_time = -1

    __key_pressed_sig = None
    __focus_sig = None

    def __update_interface(self):
        """If __interface is None, set a proxy interface object and connect
        to the key pressed signal."""

        if self.__interface:
            return self.__interface

        bus = get_bus()
        if not bus:
            return

        for desc in self.DBUS_IFACES:
            try:
                obj = bus.get_object(self.DBUS_NAME, desc["path"])
                iface = dbus.Interface(obj, desc["interface"])
                # try to call a method to test the interface
                iface.ReleaseMediaPlayerKeys(self.APP_NAME)
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

        bus = get_bus()
        if not bus:
            return

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
        if application != self.APP_NAME:
            return

        from quodlibet.player import playlist as player

        # TODO: Rewind, FastForward, Repeat, Shuffle
        if action == "Play":
            if player.song is None:
                player.reset()
            else:
                player.paused ^= True
        elif action == "Pause":
            player.paused = True
        elif action == "Stop":
            player.paused = True
            player.seek(0)
        elif action == "Next":
            player.next()
        elif action == "Previous":
            player.previous()

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

        try: iface.GrabMediaPlayerKeys(self.APP_NAME, self.__grab_time)
        except dbus.DBusException: pass

    def __release(self):
        """Tells gsd that we don't want events anymore and
        removes all signal matches"""

        if self.__key_pressed_sig:
            self.__key_pressed_sig.remove()
            self.__key_pressed_sig = None

        if self.__interface:
            try: self.__interface.ReleaseMediaPlayerKeys(self.APP_NAME)
            except dbus.DBusException: pass
            self.__interface = None

    def __focus_event(self, window, param):
        if window.get_property(param.name):
            self.__grab()

    def enabled(self):
        self.__grab()
        self.__enable_watch()
        self.__focus_sig = widgets.main.connect("notify::is-active",
                                                self.__focus_event)

    def disabled(self):
        widgets.main.disconnect(self.__focus_sig)
        self.__disable_watch()
        self.__release()
        self.__grab_time = -1
