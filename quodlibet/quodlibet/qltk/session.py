# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gio
from gi.repository import GLib

from quodlibet import app
from quodlibet.util import print_d, print_w


def init(app_id):
    try:
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        session_mgr = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            'org.gnome.SessionManager', '/org/gnome/SessionManager',
            'org.gnome.SessionManager', None)
        client_path = session_mgr.RegisterClient('(ss)', app_id, "")
        if client_path is None:
            # https://github.com/quodlibet/quodlibet/issues/2435
            print_w("Broken session manager implementation, likely LXDE")
            return

        client_priv = Gio.DBusProxy.new_sync(
            bus, Gio.DBusProxyFlags.NONE, None,
            'org.gnome.SessionManager', client_path,
            'org.gnome.SessionManager.ClientPrivate', None)

        def g_signal_cb(proxy, sender, signal, args):
            if signal == 'EndSession':
                print_d("GSM sent EndSession: going down")
                client_priv.EndSessionResponse('(bs)', True, "")
                app.quit()
            elif signal == 'QueryEndSession':
                print_d("GSM sent QueryEndSession")
                client_priv.EndSessionResponse('(bs)', True, "")

        client_priv.connect('g-signal', g_signal_cb)
    except GLib.Error:
        print_d("Connecting with the gnome session manager failed")
    else:
        print_d("Connected with gnome session manager: %s" % client_path)
