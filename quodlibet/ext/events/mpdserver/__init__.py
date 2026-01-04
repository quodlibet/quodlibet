# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

if os.name == "nt":
    from quodlibet.plugins import PluginNotSupportedError

    # we are missing socket.fromfd on Windows
    raise PluginNotSupportedError

import socket

from gi.repository import Gtk

from quodlibet import _
from quodlibet.plugins import PluginConfigMixin
from quodlibet.plugins.events import EventPlugin
from quodlibet import app
from quodlibet import qltk
from quodlibet import config
from quodlibet.qltk.entry import UndoEntry
from quodlibet.qltk import Icons
from quodlibet.util import print_w, print_d
from quodlibet.util.thread import call_async, Cancellable

from .main import MPDServer
from .tcpserver import ServerError
from .avahi import AvahiService, AvahiError


def fetch_local_ip():
    """Returns a guess for the local IP"""

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        addr = s.getsockname()[0]
        s.close()
    except OSError:
        addr = "?.?.?.?"
    return addr


DEFAULT_PORT = 6600


def get_port_num():
    return config.getint("plugins", "mpdserver_port", DEFAULT_PORT)


def set_port_num(value):
    return config.set("plugins", "mpdserver_port", str(value))


class MPDServerPlugin(EventPlugin, PluginConfigMixin):
    PLUGIN_ID = "mpd_server"
    PLUGIN_NAME = _("MPD Server")
    PLUGIN_DESC = _(
        "Allows remote control of Quod Libet using an MPD Client. "
        "Streaming, playlist and library management "
        "are not supported."
    )
    PLUGIN_ICON = Icons.NETWORK_WORKGROUP

    CONFIG_SECTION = "mpdserver"

    _server = None

    def PluginPreferences(self, parent):
        table = Gtk.Table(n_rows=3, n_columns=3)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        label = Gtk.Label(label=_("_Port:"), use_underline=True)
        label.set_xalign(0.0)
        label.set_yalign(0.5)
        table.attach(
            label,
            0,
            1,
            1,
            2,
            xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK,
        )

        entry = UndoEntry()
        entry.set_text(str(get_port_num()))

        def validate_port(entry, text, *args):
            try:
                int(text)
            except ValueError:
                entry.stop_emission("insert-text")

        entry.connect("insert-text", validate_port)

        def port_activate(entry, *args):
            try:
                port_num = int(entry.get_text())
            except ValueError as e:
                print_w(e)
            else:
                if get_port_num() != port_num:
                    set_port_num(port_num)
                    self._refresh()

        entry.connect_after("activate", port_activate)
        entry.connect_after("focus-out-event", port_activate)

        table.attach(entry, 1, 2, 1, 2)

        port_revert = Gtk.Button()
        port_revert.add(
            Gtk.Image.new_from_icon_name(Icons.DOCUMENT_REVERT, Gtk.IconSize.NORMAL)
        )

        def port_revert_cb(button, entry):
            entry.set_text(str(DEFAULT_PORT))
            entry.emit("activate")

        port_revert.connect("clicked", port_revert_cb, entry)
        table.attach(port_revert, 2, 3, 1, 2, xoptions=Gtk.AttachOptions.SHRINK)

        label = Gtk.Label(label=_("Local _IP:"), use_underline=True)
        label.set_xalign(0.0)
        label.set_yalign(0.5)
        table.attach(
            label,
            0,
            1,
            0,
            1,
            xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK,
        )

        label = Gtk.Label(label=_("P_assword:"), use_underline=True)
        label.set_xalign(0.0)
        label.set_yalign(0.5)
        table.attach(
            label,
            0,
            1,
            2,
            3,
            xoptions=Gtk.AttachOptions.FILL | Gtk.AttachOptions.SHRINK,
        )

        entry = UndoEntry()
        entry.set_text(self.config_get("password"))
        entry.connect("changed", self.config_entry_changed, "password")

        table.attach(entry, 1, 3, 2, 3)

        label = Gtk.Label()
        label.set_padding(6, 6)
        label.set_xalign(0.0)
        label.set_yalign(0.5)
        label.set_selectable(True)
        label.set_label("...")
        table.attach(label, 1, 3, 0, 1)

        cancel = Cancellable()
        label.connect("destroy", lambda *x: cancel.cancel())
        call_async(fetch_local_ip, cancel, label.set_label)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        clients = Gtk.Label()
        clients.set_padding(6, 6)
        clients.set_markup("""\
\u2022 <a href="https://play.google.com/store/apps/details?id=com.\
namelessdev.mpdroid">MPDroid</a> (Android)
\u2022 <a href="https://play.google.com/store/apps/details?id=org.\
gateshipone.malp">M.A.L.P.</a> (Android)
""")
        clients.set_xalign(0)
        clients.set_yalign(0)

        box.prepend(qltk.Frame(_("Connection"), child=table))
        box.prepend(qltk.Frame(_("Tested Clients"), child=clients))
        return box

    def _refresh(self):
        # only restart if it was running
        if self._server:
            self._disable_server()
            self._enable_server()
            self._update_avahi()

    def _enable_server(self):
        port_num = get_port_num()
        print_d("Starting MPD server on port %d" % port_num)
        self._server = MPDServer(app, self, port_num)
        try:
            self._server.start()
        except ServerError as e:
            print_w(e)

    def _disable_server(self):
        print_d("Stopping MPD server")
        self._server.stop()
        self._server = None

    def _update_avahi(self):
        assert self._avahi

        port_num = get_port_num()
        try:
            self._avahi.register(app.name, port_num, "_mpd._tcp")
        except AvahiError as e:
            print_w(e)

    def enabled(self):
        self._enable_server()
        self._avahi = AvahiService()
        self._update_avahi()

    def disabled(self):
        self._avahi.unregister()
        self._avahi = None
        self._disable_server()
