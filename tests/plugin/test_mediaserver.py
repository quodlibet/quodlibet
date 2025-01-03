# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk

try:
    import dbus
except ImportError:
    dbus = None

from tests import skipUnless
from tests.plugin import PluginTestCase, init_fake_app, destroy_fake_app

from quodlibet import config


@skipUnless(dbus, "no dbus module")
class TMediaServer(PluginTestCase):
    def setUp(self):
        config.init()
        init_fake_app()

        self.plugin = self.plugins["mediaserver"].cls
        self.m = self.plugin()
        self.m.enabled()
        self._replies = []
        self._args = {"reply_handler": self._reply, "error_handler": self._error}

    def tearDown(self):
        bus = dbus.SessionBus()
        self.assertTrue(bus.name_has_owner("org.gnome.UPnP.MediaServer2.QuodLibet"))
        self.m.disabled()
        self.assertFalse(bus.name_has_owner("org.gnome.UPnP.MediaServer2.QuodLibet"))
        del self.m

        destroy_fake_app()
        config.quit()

    def _reply(self, *args):
        self._replies.append(args)

    def _error(self, *args):
        assert not args

    def _wait(self):
        while not self._replies:
            Gtk.main_iteration_do(False)
        return self._replies.pop(0)

    def _entry_props_iface(self):
        bus = dbus.SessionBus()
        obj = bus.get_object(
            "org.gnome.UPnP.MediaServer2.QuodLibet",
            "/org/gnome/UPnP/MediaServer2/QuodLibet",
        )
        return dbus.Interface(obj, dbus_interface="org.freedesktop.DBus.Properties")

    def test_entry_name(self):
        iface = self._entry_props_iface()
        iface.Get("org.gnome.UPnP.MediaObject2", "DisplayName", **self._args)
        assert "Quod Libet" in self._wait()[0]

    def test_name_owner(self):
        bus = dbus.SessionBus()
        self.assertTrue(bus.name_has_owner("org.gnome.UPnP.MediaServer2.QuodLibet"))
