# Copyright 2014 Christoph Reiter <reiter.christoph@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

import os

if os.name == "nt":
    from quodlibet.plugins import PluginNotSupportedError
    # we are missing socket.fromfd on Windows
    raise PluginNotSupportedError

import socket
import threading

from gi.repository import Gtk, GLib

from quodlibet.plugins.events import EventPlugin
from quodlibet import app
from quodlibet import qltk
from quodlibet import config
from quodlibet.qltk.entry import UndoEntry

from .main import MPDServer
from .tcpserver import ServerError
from .avahi import AvahiService, AvahiError


def fill_ip(entry):
    """Fill GtkEntry with the local IP. Can be called from a thread."""

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        addr = s.getsockname()[0]
        s.close()
    except EnvironmentError:
        addr = "?.?.?.?"

    def idle_fill():
        if entry.get_realized():
            entry.set_text(addr)

    GLib.idle_add(idle_fill)


DEFAULT_PORT = 6600


def get_port_num():
    return config.getint("plugins", "mpdserver_port", DEFAULT_PORT)


def set_port_num(value):
    return config.set("plugins", "mpdserver_port", str(value))


class MPDServerPlugin(EventPlugin):
    PLUGIN_ID = "mpd_server"
    PLUGIN_NAME = _("MPD Server")
    PLUGIN_DESC = _("Control Quod Libet remotely using a MPD Client. "
        "Streaming, playlist and library management are not supported.")
    PLUGIN_ICON = Gtk.STOCK_CONNECT

    def PluginPreferences(self, parent):
        table = Gtk.Table(2, 3)
        table.set_col_spacings(6)
        table.set_row_spacings(6)

        label = Gtk.Label(label=_("_Port:"), use_underline=True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 0, 1,
                     xoptions=Gtk.AttachOptions.FILL |
                     Gtk.AttachOptions.SHRINK)

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
                print_w(str(e))
            else:
                if get_port_num() != port_num:
                    set_port_num(port_num)
                    self._refresh()

        entry.connect_after("activate", port_activate)
        entry.connect_after("focus-out-event", port_activate)

        table.attach(entry, 1, 2, 0, 1)

        port_revert = Gtk.Button()
        port_revert.add(Gtk.Image.new_from_stock(
            Gtk.STOCK_REVERT_TO_SAVED, Gtk.IconSize.MENU))

        def port_revert_cb(button, entry):
            entry.set_text(str(DEFAULT_PORT))
            entry.emit("activate")

        port_revert.connect("clicked", port_revert_cb, entry)
        table.attach(
            port_revert, 2, 3, 0, 1, xoptions=Gtk.AttachOptions.SHRINK)

        label = Gtk.Label(label=_("Local _IP:"), use_underline=True)
        label.set_alignment(0.0, 0.5)
        table.attach(label, 0, 1, 1, 2,
                     xoptions=Gtk.AttachOptions.FILL |
                     Gtk.AttachOptions.SHRINK)

        entry = UndoEntry()
        entry.set_text("...")
        entry.set_editable(False)
        table.attach(entry, 1, 3, 1, 2)

        threading.Thread(target=fill_ip, args=(entry,)).start()

        box = Gtk.VBox(spacing=12)

        clients = Gtk.Label()
        clients.set_padding(6, 6)
        clients.set_markup(_(u"""\
\u2022 <a href="https://play.google.com/store/apps/details?id=com.\
namelessdev.mpdroid">MPDroid 1.06</a> (Android)<small>

</small>\u2022 <a href="http://sonata.berlios.de/">Sonata 1.6</a> (Linux)\
"""))
        clients.set_alignment(0, 0)

        box.pack_start(
            qltk.Frame(_("Connection"), child=table), False, True, 0)
        box.pack_start(
            qltk.Frame(_("Tested Clients"), child=clients), True, True, 0)
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
        self._server = MPDServer(app, port_num)
        try:
            self._server.start()
        except ServerError as e:
            print_w(str(e))

    def _disable_server(self):
        print_d("Stopping MPD server")
        self._server.stop()
        self._server = None

    def _update_avahi(self):
        assert self._avahi

        port_num = get_port_num()
        try:
            self._avahi.register("quodlibet", port_num, "_mpd._tcp")
        except AvahiError as e:
            print_w(str(e))

    def enabled(self):
        self._enable_server()
        self._avahi = AvahiService()
        self._update_avahi()

    def disabled(self):
        self._avahi.unregister()
        self._avahi = None
        self._disable_server()
