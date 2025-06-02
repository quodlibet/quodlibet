# Copyright 2014 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
from gi.repository import Gtk, GLib

from quodlibet import _
from quodlibet import print_d, app, config
from quodlibet.plugins import PluginConfigMixin
from quodlibet.qltk import Message
from quodlibet.qltk.x import Frame
from quodlibet.qltk.entry import UndoEntry
from quodlibet.util.library import get_scan_dirs

from .util import GetPlayerDialog
from .server import SqueezeboxServer, SqueezeboxError


class SqueezeboxPluginMixin(PluginConfigMixin):
    """
    All the Squeezebox connection / communication code in one delicious class
    """

    # Maintain a singleton; we only support one SB server live in QL
    server = None

    # We want all derived classes to share the config section
    CONFIG_SECTION = "squeezebox"

    @classmethod
    def _get_ql_base_dir(cls):
        dirs = get_scan_dirs()
        return os.path.realpath(dirs[0]) if dirs else ""

    @classmethod
    def get_sb_path(cls, song):
        """Gets a SB path to `song` by simple substitution"""
        path = song("~filename")
        return path.replace(cls._get_ql_base_dir(), cls.server.get_library_dir())

    @classmethod
    def post_reconnect(cls):
        pass

    @staticmethod
    def _show_dialog(dialog_type, msg):
        dialog = Message(dialog_type, app.window, "Squeezebox", msg)
        dialog.connect("response", lambda dia, resp: dia.destroy())
        dialog.show()

    @staticmethod
    def quick_dialog(msg, dialog_type=Gtk.MessageType.INFO):
        GLib.idle_add(SqueezeboxPluginMixin._show_dialog, dialog_type, msg)

    @classmethod
    def set_player(cls, val):
        cls.server.current_player = val
        cls.config_set("current_player", val)
        print_d("Setting player to #%d (%s)" % (val, cls.server.players[val]))

    @classmethod
    def check_settings(cls, button):
        cls.init_server()
        if cls.server.is_connected:
            ret = 0
            if len(cls.server.players) > 1:
                dialog = GetPlayerDialog(
                    app.window, cls.server.players, cls.server.current_player
                )
                ret = dialog.run() or 0
            else:
                cls.quick_dialog(
                    _("Squeezebox OK. Using the only player (%s).")
                    % cls.server.players[0]
                )
            cls.set_player(ret)
            # TODO: verify sanity of SB library path

            # Manage the changeover as best we can...
            cls.post_reconnect()

        else:
            cls.quick_dialog(
                _("Couldn't connect to %s") % (cls.server,), Gtk.MessageType.ERROR
            )

    @classmethod
    def PluginPreferences(cls, parent):
        def value_changed(entry, key):
            if entry.get_property("sensitive"):
                cls.server.config[key] = entry.get_text()
                config.set("plugins", "squeezebox_" + key, entry.get_text())

        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        if not cls.server:
            cls.init_server()
        cfg = cls.server.config

        # Tabulate all settings for neatness
        table = Gtk.Table(n_rows=3, n_columns=2)
        table.set_col_spacings(6)
        table.set_row_spacings(6)
        rows = []

        ve = UndoEntry()
        ve.set_text(cfg["hostname"])
        ve.connect("changed", value_changed, "server_hostname")
        lbl = Gtk.Label(label=_("Hostname:"), use_underline=True)
        lbl.set_mnemonic_widget(ve)
        rows.append((lbl, ve))

        ve = UndoEntry()
        ve.set_width_chars(5)
        ve.set_text(str(cfg["port"]))
        ve.connect("changed", value_changed, "server_port")
        lbl = Gtk.Label(label=_("Port:"), use_underline=True)
        lbl.set_mnemonic_widget(ve)
        rows.append((lbl, ve))

        ve = UndoEntry()
        ve.set_text(cfg["user"])
        ve.connect("changed", value_changed, "server_user")
        lbl = Gtk.Label(label=_("Username:"), use_underline=True)
        lbl.set_mnemonic_widget(ve)
        rows.append((lbl, ve))

        ve = UndoEntry()
        ve.set_text(str(cfg["password"]))
        ve.connect("changed", value_changed, "server_password")
        lbl = Gtk.Label(label=_("Password:"), use_underline=True)
        lbl.set_mnemonic_widget(ve)
        rows.append((lbl, ve))

        ve = UndoEntry()
        ve.set_text(str(cfg["library_dir"]))
        ve.set_tooltip_text(_("Library directory the server connects to"))
        ve.connect("changed", value_changed, "server_library_dir")
        lbl = Gtk.Label(label=_("Library path:"), use_underline=True)
        lbl.set_mnemonic_widget(ve)
        rows.append((lbl, ve))

        for row, (label, entry) in enumerate(rows):
            label.set_alignment(0.0, 0.5)
            table.attach(label, 0, 1, row, row + 1, xoptions=Gtk.AttachOptions.FILL)
            table.attach(entry, 1, 2, row, row + 1)

        # Add verify button
        button = Gtk.Button(label=_("_Verify settings"), use_underline=True)
        button.set_sensitive(cls.server is not None)
        button.connect("clicked", cls.check_settings)
        table.attach(button, 0, 2, row + 1, row + 2)

        # Server settings Frame
        cfg_frame = Frame(_("Squeezebox Server"), table)

        vb.prepend(cfg_frame, True, True, 0)
        debug = cls.ConfigCheckButton(_("Debug"), "debug")
        vb.prepend(debug, True, True, 0)
        return vb

    @classmethod
    def init_server(cls):
        """Initialises a server, and connects to check if it's alive"""
        try:
            cur = int(cls.config_get("current_player", 0))
        except ValueError:
            cur = 0
        cls.server = SqueezeboxServer(
            hostname=cls.config_get("server_hostname", "localhost"),
            port=cls.config_get("server_port", 9090),
            user=cls.config_get("server_user", ""),
            password=cls.config_get("server_password", ""),
            library_dir=cls.config_get("server_library_dir", cls._get_ql_base_dir()),
            current_player=cur,
            debug=cls.config_get_bool("debug", False),
        )
        try:
            ver = cls.server.get_version()
            if cls.server.is_connected:
                print_d(
                    "Squeezebox server version: %s. Current player: #%d (%s)."
                    % (ver, cur, cls.server.get_players()[cur]["name"])
                )
        except (IndexError, KeyError, SqueezeboxError) as e:
            print_d(f"Couldn't get player info ({e}).")
