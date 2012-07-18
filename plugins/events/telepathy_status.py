# -*- coding: utf-8 -*-
# Quod Libet Telepathy Plugin
# Copyright 2012 Nick Boultbee
#
# Thanks also to
# http://blogs.gnome.org/danni/2011/11/17/let-us-not-mourn-telepathy-python/
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import dbus
import gtk

from quodlibet.parse._pattern import Pattern
from quodlibet.qltk.entry import UndoEntry
from quodlibet import qltk
from quodlibet import util

from quodlibet import config
from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins import PluginManager as PM


AM_PATH = "/org/freedesktop/Telepathy/AccountManager"
AM_NAME = "org.freedesktop.Telepathy.AccountManager"
AM_IFACE = "org.freedesktop.Telepathy.AccountManager"
AC_IFACE = "org.freedesktop.Telepathy.Account"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
CONN_PRESENCE_TYPE_AVAILABLE = 2


def get_active_account_paths():
    bus = dbus.SessionBus()
    bus_object = bus.get_object(AM_NAME, AM_PATH)
    bus_iface = dbus.Interface(bus_object, dbus_interface=PROPS_IFACE)
    return bus_iface.Get(AM_IFACE, "ValidAccounts")


def set_accounts_requested_presence(paths, status, message):
    bus = dbus.SessionBus()
    for path in paths:
        bus_object = bus.get_object(AM_NAME, path)
        bus_iface = dbus.Interface(bus_object, dbus_interface=PROPS_IFACE)
        presence_type = dbus.UInt32(CONN_PRESENCE_TYPE_AVAILABLE)
        value = dbus.Struct([presence_type, status, message])
        bus_iface.Set(AC_IFACE, "RequestedPresence", value)


class PluginConfigMixin(object):
    """Mixin for storage and editing of plugin config in a standard way"""

    def _cfg_key(self, name):
        return "%s_%s" % (self.PLUGIN_ID, name)

    def cfg_get(self, name, default=None):
        """Gets a config string value for this plugin"""
        try:
            return config.get(PM.CONFIG_SECTION, self._cfg_key(name))
        except config.error:
            # Set the missing config
            config.set("plugins", "%s_%s" % (self.PLUGIN_ID, name), default)
            return default

    def cfg_set(self, name, value):
        """Saves a config string value for this plugin"""
        try:
            config.set(PM.CONFIG_SECTION, self._cfg_key(name), value)
        except config.error:
            print_d("Couldn't set config item '%s' to %r" % (name, value))

    def cfg_get_bool(self, name, default=False):
        """Gets a config boolean for this plugin"""
        return config.getboolean(PM.CONFIG_SECTION, self._cfg_key(name),
                                 default)

    def cfg_entry_changed(self, entry, key):
        """React to a change in an gtk.Entry (by saving it to config)"""
        if entry.get_property('sensitive'):
            self.cfg_set(key, entry.get_text())


class TelepathyStatusPlugin(EventPlugin, PluginConfigMixin):
    PLUGIN_ID = "Telepathy Status"
    PLUGIN_NAME = _("Telepathy Status Messages")
    PLUGIN_DESC = _("Updates all Telepathy-based IM accounts (as configured in "
                    "Empathy etc) with a status message based on current song.")
    PLUGIN_ICON = gtk.STOCK_CONNECT
    PLUGIN_VERSION = "0.1"

    DEFAULT_PAT = "♫ <~artist~title> ♫"
    DEFAULT_PAT_PAUSED = "<~artist~title> [%s]" % _("paused")
    CFG_STATUS_SONGLESS = 'no_song_text'
    CFG_LEAVE_STATUS = "leave_status"
    CFG_PAT_PLAYING = "playing_pattern"
    CFG_PAT_PAUSED = "paused_pattern"

    def _set_status(self, text):
        print_d("Setting status to \"%s\"" % text)
        self.status = text
        try:
            accounts = get_active_account_paths()
            set_accounts_requested_presence(accounts, "available", text)
        except dbus.DBusException:
            print_d("setting failed")
            util.print_exc()

    def plugin_on_song_started(self, song):
        self.song = song
        pat_str = self.cfg_get(self.CFG_PAT_PLAYING, self.DEFAULT_PAT)
        pattern = Pattern(pat_str)
        status = (pattern.format(song) if song
                       else self.cfg_get(self.CFG_STATUS_SONGLESS, ""))
        self._set_status(status)

    def plugin_on_paused(self):
        pat_str = self.cfg_get(self.CFG_PAT_PAUSED, self.DEFAULT_PAT_PAUSED)
        pattern = Pattern(pat_str)
        self.status = pattern.format(self.song) if self.song else ""
        self._set_status(self.status)

    def plugin_on_unpaused(self):
        self.plugin_on_song_started(self.song)

    def disabled(self):
        if self.status:
            self._set_status(self.cfg_get(self.CFG_STATUS_SONGLESS))

    def enabled(self):
        print_d("Setting up Telepathy hooks...")
        self.song = None
        self.status = ""

    def PluginPreferences(self, parent):
        outer_vb = gtk.VBox(spacing=12)
        vb = gtk.VBox(spacing=12)

        # Playing
        hb = gtk.HBox(spacing=6)
        entry = UndoEntry()
        entry.set_text(self.cfg_get(self.CFG_PAT_PLAYING, self.DEFAULT_PAT))
        entry.connect('changed', self.cfg_entry_changed, self.CFG_PAT_PLAYING)
        lbl = gtk.Label(_("Playing:"))
        entry.set_tooltip_markup(_("Status text when a song is started. "
                                 "Accepts QL Patterns e.g. <tt>%s</tt>")
                                 % util.escape("<~artist~title>"))
        lbl.set_mnemonic_widget(entry)
        hb.pack_start(lbl, expand=False)
        hb.pack_start(entry)
        vb.pack_start(hb)

        # Playing
        hb = gtk.HBox(spacing=6)
        entry = UndoEntry()
        entry.set_text(self.cfg_get(self.CFG_PAT_PAUSED,
                                    self.DEFAULT_PAT_PAUSED))
        entry.connect('changed', self.cfg_entry_changed, self.CFG_PAT_PAUSED)
        lbl = gtk.Label(_("Paused:"))
        entry.set_tooltip_markup(_("Status text when a song is paused. "
                                   "Accepts QL Patterns e.g. <tt>%s</tt>")
                                   % util.escape("<~artist~title>"))
        lbl.set_mnemonic_widget(entry)
        hb.pack_start(lbl, expand=False)
        hb.pack_start(entry)
        vb.pack_start(hb)

        # No Song
        hb = gtk.HBox(spacing=6)
        entry = UndoEntry()
        entry.set_text(self.cfg_get(self.CFG_STATUS_SONGLESS, ""))
        entry.connect('changed', self.cfg_entry_changed,
                      self.CFG_STATUS_SONGLESS)
        entry.set_tooltip_text(
                _("Plain text for status when there is no current song"))
        lbl = gtk.Label(_("No song:"))
        lbl.set_mnemonic_widget(entry)
        hb.pack_start(lbl, expand=False)
        hb.pack_start(entry)
        vb.pack_start(hb)

        # Frame
        frame = gtk.Frame(_("Status Patterns"))
        frame.add(vb)
        vb.set_border_width(9)
        outer_vb.pack_start(frame, expand=False)

        return outer_vb
