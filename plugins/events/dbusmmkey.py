# -*- coding: utf-8 -*-
# Copyright 2007 Ronny Haryanto <ronny at haryan.to>
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
#
# $Id$

import dbus
from plugins.events import EventPlugin
from player import playlist as player

class DBusMMKey(EventPlugin):
    PLUGIN_ID = "DBusMMKey"
    PLUGIN_NAME = _("DBus Multimedia Keys")
    PLUGIN_DESC = _("Enable DBus-based Multimedia Shortcut Keys.\n"
                    "By Ronny Haryanto")
    PLUGIN_VERSION = "0.2"

    def __init__(self):
        self.mmkc = MMKeysControl(player)
        self.bus = None
        self.bus_object_old = None
        self.bus_object_new = None

    def enabled(self):
        if self.bus is None or self.bus_object is None:
            self.bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
            # Work around the gnome-settings-daemon dbus interface
            # changing between 2.20 and 2.22 by connecting to both
            # the old and new object.
            self.bus_object_old = self.bus.get_object(
                'org.gnome.SettingsDaemon', '/org/gnome/SettingsDaemon')
            self.bus_object_old.connect_to_signal("MediaPlayerKeyPressed", self.mmkc.action)
            self.bus_object_new = self.bus.get_object(
                'org.gnome.SettingsDaemon', '/org/gnome/SettingsDaemon/MediaKeys')
            self.bus_object_new.connect_to_signal("MediaPlayerKeyPressed", self.mmkc.action)
        self.mmkc.set_enabled(True)

    def disabled(self):
        self.mmkc.set_enabled(False)

class MMKeysControl(object):
    def __init__(self, player):
        self.player = player
        self._enabled = False

    def set_enabled(self, state):
        self._enabled = state

    def action(self, *mmkeys):
        for mmk in mmkeys:
            if self._enabled:
                if mmk == "Play":
                    if self.player.song is None:
                        self.player.reset()
                    else:
                        self.player.paused ^= True
                elif mmk == "Stop":
                    self.player.paused = True
                    self.player.seek(0)
                elif mmk == "Next":
                    self.player.next()
                elif mmk == "Previous":
                    self.player.previous()
