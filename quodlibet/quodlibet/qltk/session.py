# -*- coding: utf-8 -*-
# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

try:
    import dbus
    dbus
except ImportError:
    dbus = None

from quodlibet import app
from quodlibet.util import print_d, print_w


def init(app_id):
    if not dbus:
        return

    try:
        bus = dbus.Bus(dbus.Bus.TYPE_SESSION)
        manager = bus.get_object("org.gnome.SessionManager",
                                 "/org/gnome/SessionManager")
        iface = dbus.Interface(manager, "org.gnome.SessionManager")
        client_path = iface.RegisterClient(app_id, "")
        if client_path is None:
            # https://github.com/quodlibet/quodlibet/issues/2435
            print_w("Broken session manager implementation, likely LXDE")
            return

        client = bus.get_object("org.gnome.SessionManager", client_path)
        client_priv = dbus.Interface(client,
                                     "org.gnome.SessionManager.ClientPrivate")

        def end_session_cb(*args):
            print_d("GSM sent EndSession: going down")
            client_priv.EndSessionResponse(True, "")
            app.quit()

        def query_end_session_cb(*args):
            print_d("GSM sent QueryEndSession")
            client_priv.EndSessionResponse(True, "")

        client_priv.connect_to_signal("QueryEndSession", query_end_session_cb)
        client_priv.connect_to_signal("EndSession", end_session_cb)
    except dbus.DBusException:
        print_d("Connecting with the gnome session manager failed")
    else:
        print_d("Connected with gnome session manager: %s" % client_path)
