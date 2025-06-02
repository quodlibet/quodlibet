# Quod Libet Telepathy Plugin
# Copyright 2012 Christoph Reiter
#      2012,2016 Nick Boultbee
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

from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Gtk

from quodlibet import _
from quodlibet.pattern import Pattern
from quodlibet.qltk.entry import UndoEntry
from quodlibet import util
from quodlibet import qltk

from quodlibet.plugins.events import EventPlugin
from quodlibet.plugins import PluginConfigMixin
from quodlibet.util.dprint import print_d
from quodlibet.qltk import Icons


AM_PATH = "/org/freedesktop/Telepathy/AccountManager"
AM_NAME = "org.freedesktop.Telepathy.AccountManager"
AM_IFACE = "org.freedesktop.Telepathy.AccountManager"
AC_IFACE = "org.freedesktop.Telepathy.Account"
PROPS_IFACE = "org.freedesktop.DBus.Properties"
CONN_PRESENCE_TYPE_AVAILABLE = 2


def is_valid_presence_type(x):
    return x not in [0, 7, 8]


def get_active_account_paths():
    bus_iface = Gio.DBusProxy.new_for_bus_sync(
        Gio.BusType.SESSION,
        Gio.DBusProxyFlags.NONE,
        None,
        AM_NAME,
        AM_PATH,
        PROPS_IFACE,
        None,
    )
    return bus_iface.Get("(ss)", AM_IFACE, "ValidAccounts")


def set_accounts_requested_presence(paths, message):
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    for path in paths:
        bus_iface = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None, AM_NAME, path, PROPS_IFACE, None
        )
        presence_type, status = bus_iface.Get("(ss)", AC_IFACE, "CurrentPresence")[:2]
        if not is_valid_presence_type(presence_type):
            presence_type = CONN_PRESENCE_TYPE_AVAILABLE
        value = GLib.Variant("(uss)", (presence_type, status, message))
        bus_iface.Set("(ssv)", AC_IFACE, "RequestedPresence", value)


class TelepathyStatusPlugin(EventPlugin, PluginConfigMixin):
    PLUGIN_ID = "Telepathy Status"
    PLUGIN_NAME = _("Telepathy Status Messages")
    PLUGIN_DESC = _(
        "Updates all Telepathy-based IM accounts (as configured "
        "in Empathy etc) with a status message based on current "
        "song."
    )
    PLUGIN_ICON = Icons.FACE_SMILE

    DEFAULT_PAT = "♫ <~artist~title> ♫"
    DEFAULT_PAT_PAUSED = "<~artist~title> [{}]".format(_("paused"))
    CFG_STATUS_SONGLESS = "no_song_text"
    CFG_LEAVE_STATUS = "leave_status"
    CFG_PAT_PLAYING = "playing_pattern"
    CFG_PAT_PAUSED = "paused_pattern"

    def _set_status(self, text):
        print_d(f'Setting status to "{text}"...')
        self.status = text
        try:
            accounts = get_active_account_paths()
            # TODO: account filtering
            set_accounts_requested_presence(accounts, text)
        except GLib.Error:
            print_d("...but setting failed")
            util.print_exc()

    def plugin_on_song_started(self, song):
        self.song = song
        pat_str = self.config_get(self.CFG_PAT_PLAYING, self.DEFAULT_PAT)
        pattern = Pattern(pat_str)
        status = (
            pattern.format(song)
            if song
            else self.config_get(self.CFG_STATUS_SONGLESS, "")
        )
        self._set_status(status)

    def plugin_on_paused(self):
        pat_str = self.config_get(self.CFG_PAT_PAUSED, self.DEFAULT_PAT_PAUSED)
        pattern = Pattern(pat_str)
        self.status = pattern.format(self.song) if self.song else ""
        self._set_status(self.status)

    def plugin_on_unpaused(self):
        self.plugin_on_song_started(self.song)

    def disabled(self):
        if self.status:
            self._set_status(self.config_get(self.CFG_STATUS_SONGLESS))

    def enabled(self):
        self.song = None
        self.status = ""

    def PluginPreferences(self, parent):
        outer_vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        # Playing
        hb = Gtk.Box(spacing=6)
        entry = UndoEntry()
        entry.set_text(self.config_get(self.CFG_PAT_PLAYING, self.DEFAULT_PAT))
        entry.connect("changed", self.config_entry_changed, self.CFG_PAT_PLAYING)
        lbl = Gtk.Label(label=_("Playing:"))
        entry.set_tooltip_markup(
            _("Status text when a song is started. Accepts QL Patterns e.g. %s")
            % util.monospace("<~artist~title>")
        )
        lbl.set_mnemonic_widget(entry)
        hb.prepend(lbl, False, True, 0)
        hb.prepend(entry, True, True, 0)
        vb.prepend(hb, True, True, 0)

        # Paused
        hb = Gtk.Box(spacing=6)
        entry = UndoEntry()
        entry.set_text(self.config_get(self.CFG_PAT_PAUSED, self.DEFAULT_PAT_PAUSED))
        entry.connect("changed", self.config_entry_changed, self.CFG_PAT_PAUSED)
        lbl = Gtk.Label(label=_("Paused:"))
        entry.set_tooltip_markup(
            _("Status text when a song is paused. Accepts QL Patterns e.g. %s")
            % util.monospace("<~artist~title>")
        )
        lbl.set_mnemonic_widget(entry)
        hb.prepend(lbl, False, True, 0)
        hb.prepend(entry, True, True, 0)
        vb.prepend(hb, True, True, 0)

        # No Song
        hb = Gtk.Box(spacing=6)
        entry = UndoEntry()
        entry.set_text(self.config_get(self.CFG_STATUS_SONGLESS, ""))
        entry.connect("changed", self.config_entry_changed, self.CFG_STATUS_SONGLESS)
        entry.set_tooltip_text(_("Plain text for status when there is no current song"))
        lbl = Gtk.Label(label=_("No song:"))
        lbl.set_mnemonic_widget(entry)
        hb.prepend(lbl, False, True, 0)
        hb.prepend(entry, True, True, 0)
        vb.prepend(hb, True, True, 0)

        # Frame
        frame = qltk.Frame(_("Status Patterns"), child=vb)
        outer_vb.prepend(frame, False, True, 0)

        return outer_vb
