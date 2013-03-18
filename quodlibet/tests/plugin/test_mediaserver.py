# Copyright 2013 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of version 2 of the GNU General Public License as
# published by the Free Software Foundation.

from gi.repository import Gtk

import dbus

from tests import add
from tests.plugin import PluginTestCase

from quodlibet import library
from quodlibet import app


class TMediaServer(PluginTestCase):
    @classmethod
    def setUpClass(cls):
        app.library = library.init()
        cls.plugin = cls.plugins["mediaserver"]

    def setUp(self):
        self.m = self.plugin()
        self.m.enabled()
        self._replies = []
        self._args = {
            "reply_handler": self._reply,
            "error_handler": self._error
        }

    def _reply(self, *args):
        self._replies.append(args)

    def _error(self, *args):
        self.failIf(args)

    def _wait(self):
        while not self._replies:
            Gtk.main_iteration_do(False)
        return self._replies.pop(0)

    def _entry_props_iface(self):
        bus = dbus.SessionBus()
        obj = bus.get_object("org.gnome.UPnP.MediaServer2.QuodLibet",
                             "/org/gnome/UPnP/MediaServer2/QuodLibet")
        return dbus.Interface(
            obj, dbus_interface="org.freedesktop.DBus.Properties")

    def test_entry_name(self):
        iface = self._entry_props_iface()
        iface.Get("org.gnome.UPnP.MediaObject2", "DisplayName", **self._args)
        self.failUnless("Quod Libet" in self._wait()[0])

    def test_name_owner(self):
        bus = dbus.SessionBus()
        self.failUnless(
            bus.name_has_owner("org.gnome.UPnP.MediaServer2.QuodLibet"))

    def tearDown(self):
        bus = dbus.SessionBus()
        self.failUnless(
            bus.name_has_owner("org.gnome.UPnP.MediaServer2.QuodLibet"))
        self.m.disabled()
        self.failIf(
            bus.name_has_owner("org.gnome.UPnP.MediaServer2.QuodLibet"))
        del self.m


add(TMediaServer)
