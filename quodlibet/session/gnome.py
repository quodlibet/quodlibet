# Copyright 2018 Christoph Reiter
#           2025 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gio, GLib

from quodlibet import print_d, print_w
from ._base import SessionClient, SessionError


class GnomeSessionClient(SessionClient):
    DBUS_NAME = "org.gnome.SessionManager"
    DBUS_OBJECT_PATH = "/org/gnome/SessionManager"
    DBUS_MAIN_INTERFACE = "org.gnome.SessionManager"
    DBUS_CLIENT_INTERFACE = "org.gnome.SessionManager.ClientPrivate"

    def __init__(self):
        super().__init__()
        self._client_priv = None
        self._client_path = None
        self._sig_id = None

    def open(self, app):
        print_d("Connecting with gnome session manager")
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            session_mgr = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                self.DBUS_NAME,
                self.DBUS_OBJECT_PATH,
                self.DBUS_MAIN_INTERFACE,
                None,
            )
            if session_mgr.get_name_owner() is None:
                raise SessionError(f"{self.DBUS_NAME} unowned")
            client_path = session_mgr.RegisterClient("(ss)", app.id, "")
            if client_path is None:
                # https://github.com/quodlibet/quodlibet/issues/2435
                raise SessionError("Broken session manager implementation, likely LXDE")

            client_priv = Gio.DBusProxy.new_sync(
                bus,
                Gio.DBusProxyFlags.NONE,
                None,
                self.DBUS_NAME,
                client_path,
                self.DBUS_CLIENT_INTERFACE,
                None,
            )

            def g_signal_cb(proxy, sender, signal, args):
                if signal == "EndSession":
                    print_d("GSM sent EndSession: going down")
                    proxy.EndSessionResponse("(bs)", True, "")
                    app.quit()
                elif signal == "Stop":
                    print_d("GSM sent Stop: going down")
                    app.quit()
                elif signal == "QueryEndSession":
                    print_d("GSM sent QueryEndSession")
                    proxy.EndSessionResponse("(bs)", True, "")

            self._sig_id = client_priv.connect("g-signal", g_signal_cb)
            self._client_priv = client_priv
            self._client_path = client_path
            print_d(f"Connected with gnome session manager: {client_path}")
        except GLib.Error as e:
            raise SessionError(e) from e

    def close(self):
        if self._client_priv is None:
            return

        if self._sig_id:
            self._client_priv.disconnect(self._sig_id)
            self._sig_id = None

        if self._client_path:
            try:
                bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
                session_mgr = Gio.DBusProxy.new_sync(
                    bus,
                    Gio.DBusProxyFlags.NONE,
                    None,
                    self.DBUS_NAME,
                    self.DBUS_OBJECT_PATH,
                    self.DBUS_MAIN_INTERFACE,
                    None,
                )
                session_mgr.UnregisterClient("(o)", self._client_path)
            except GLib.Error as e:
                print_w(str(e))
            print_d(f"Disconnected from gnome session manager: {self._client_path}")
            self._client_path = None
