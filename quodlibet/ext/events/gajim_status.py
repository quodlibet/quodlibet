# Copyright 2005-2006 Sergey Fedoseev <fedoseev.sergey@gmail.com>
# Copyright 2007 Simon Morgan <zen84964@zen.co.uk>
#           2017 Nick Boultbee
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
from quodlibet.plugins.events import EventPlugin
from quodlibet.pattern import Pattern
from quodlibet.qltk import Frame, Icons
from quodlibet import config

# Translators: statuses relating to Instant Messenger apps
_STATUSES = {
    "online": _("online"),
    "offline": _("offline"),
    "chat": _("chat"),
    "away": _("away"),
    "xa": _("xa"),
    "invisible": _("invisible"),
}


class GajimStatusMessage(EventPlugin):
    PLUGIN_ID = "Gajim status message"
    PLUGIN_NAME = _("Gajim Status Message")
    PLUGIN_DESC = _(
        "Changes Gajim status message according to what "
        "you are currently listening to."
    )
    PLUGIN_ICON = Icons.FACE_SMILE

    c_accounts = __name__ + "_accounts"
    c_paused = __name__ + "_paused"
    c_statuses = __name__ + "_statuses"
    c_pattern = __name__ + "_pattern"

    def __init__(self):
        try:
            self.accounts = config.get("plugins", self.c_accounts).split()
        except Exception:
            self.accounts = []
            config.set("plugins", self.c_accounts, "")

        try:
            self.paused = config.getboolean("plugins", self.c_paused)
        except Exception:
            self.paused = True
            config.set("plugins", self.c_paused, "True")

        try:
            self.statuses = config.get("plugins", self.c_statuses).split()
        except Exception:
            self.statuses = ["online", "chat"]
            config.set("plugins", self.c_statuses, " ".join(self.statuses))

        try:
            self.pattern = config.get("plugins", self.c_pattern)
        except Exception:
            self.pattern = "<artist> - <title>"
            config.set("plugins", self.c_pattern, self.pattern)

    def enabled(self):
        self.interface = None
        self.current = ""

    def disabled(self):
        if self.current != "":
            self.change_status(self.accounts, "")

    def change_status(self, enabled_accounts, status_message):
        if not self.interface:
            try:
                self.interface = Gio.DBusProxy.new_for_bus_sync(
                    Gio.BusType.SESSION,
                    Gio.DBusProxyFlags.NONE,
                    None,
                    "org.gajim.dbus",
                    "/org/gajim/dbus/RemoteObject",
                    "org.gajim.dbus.RemoteInterface",
                    None,
                )
            except GLib.Error:
                self.interface = None

        if self.interface:
            try:
                for account in self.interface.list_accounts():
                    status = self.interface.get_status("(s)", account)
                    if enabled_accounts != [] and account not in enabled_accounts:
                        continue
                    if status in self.statuses:
                        self.interface.change_status(
                            "(sss)", status, status_message, account
                        )
            except GLib.Error:
                self.interface = None

    def plugin_on_song_started(self, song):
        if song:
            self.current = Pattern(self.pattern) % song
        else:
            self.current = ""
        self.change_status(self.accounts, self.current)

    def plugin_on_paused(self):
        if self.paused and self.current != "":
            paused = _("paused")
            self.change_status(self.accounts, f"{self.current} [{paused}]")

    def plugin_on_unpaused(self):
        self.change_status(self.accounts, self.current)

    def accounts_changed(self, entry):
        self.accounts = entry.get_text().split()
        config.set("plugins", self.c_accounts, entry.get_text())

    def pattern_changed(self, entry):
        self.pattern = entry.get_text()
        config.set("plugins", self.c_pattern, self.pattern)

    def paused_changed(self, c):
        config.set("plugins", self.c_paused, str(c.get_active()))

    def statuses_changed(self, b):
        if b.get_active() and b.get_name() not in self.statuses:
            self.statuses.append(b.get_name())
        elif b.get_active() is False and b.get_name() in self.statuses:
            self.statuses.remove(b.get_name())
        config.set("plugins", self.c_statuses, " ".join(self.statuses))

    def PluginPreferences(self, parent):
        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        pattern_box = Gtk.Box(spacing=6)
        pattern_box.set_border_width(3)
        pattern = Gtk.Entry()
        pattern.set_text(self.pattern)
        pattern.connect("changed", self.pattern_changed)
        pattern_box.append(Gtk.Label(label=_("Pattern:")))
        pattern_box.append(pattern)

        accounts_box = Gtk.Box(spacing=3)
        accounts_box.set_border_width(3)
        accounts = Gtk.Entry()
        accounts.set_text(" ".join(self.accounts))
        accounts.connect("changed", self.accounts_changed)
        accounts.set_tooltip_text(
            _(
                "List accounts, separated by spaces, for "
                "changing status message. If none are specified, "
                "status message of all accounts will be changed."
            )
        )
        accounts_box.append(Gtk.Label(label=_("Accounts:")))
        accounts_box.append(accounts)

        c = Gtk.CheckButton(label=_("Add '[paused]'"))
        c.set_active(self.paused)
        c.connect("toggled", self.paused_changed)
        c.set_tooltip_text(
            _("If checked, '[paused]' will be added to status message on pause")
        )

        table = Gtk.Table()
        self.list = []
        i = 0
        j = 0
        for status, translated in _STATUSES.items():
            button = Gtk.CheckButton(label=translated)
            button.set_name(status)
            if status in self.statuses:
                button.set_active(True)
            button.connect("toggled", self.statuses_changed)
            self.list.append(button)
            table.attach(button, i, i + 1, j, j + 1)
            if i == 2:
                i = 0
                j += 1
            else:
                i += 1

        vb.append(pattern_box)
        vb.append(accounts_box)
        vb.append(c)
        frame = Frame(
            label=_("Statuses for which message will be changed"), child=table
        )
        vb.append(frame)
        return vb
