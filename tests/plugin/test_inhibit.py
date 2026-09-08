# Copyright 2026 Am-curious
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GLib

from quodlibet import config
from quodlibet.ext.events import inhibit
from tests import TestCase, destroy_fake_app, init_fake_app


class FakeProxy:
    def __init__(self, cookie=42):
        self.cookie = cookie
        self.inhibit_call = None
        self.uninhibit_call = None

    def Inhibit(self, signature, *args):
        self.inhibit_call = (signature, args)
        return self.cookie

    def Uninhibit(self, signature, cookie):
        self.uninhibit_call = ("Uninhibit", signature, cookie)

    def UnInhibit(self, signature, cookie):
        self.uninhibit_call = ("UnInhibit", signature, cookie)


class TSessionInhibit(TestCase):
    def setUp(self):
        config.init()
        init_fake_app()
        self.plugin = inhibit.SessionInhibit()

    def tearDown(self):
        self.plugin.plugin_on_paused()
        destroy_fake_app()
        config.quit()

    def test_gnome_backend_is_preserved(self):
        proxy = FakeProxy()
        calls = []

        def get_proxy(dbus):
            calls.append(dbus)
            return proxy

        self.plugin._SessionInhibit__get_dbus_proxy = get_proxy
        config.set(
            "plugins",
            self.plugin.CONFIG_MODE,
            inhibit.InhibitStrings.SUSPEND,
        )

        self.plugin.plugin_on_unpaused()

        self.assertEqual(calls, [self.plugin.GNOME_DBUS])
        self.assertEqual(proxy.inhibit_call[0], "(susu)")
        self.assertEqual(proxy.inhibit_call[1][-1], inhibit.InhibitFlags.SUSPEND)

        self.plugin.plugin_on_paused()
        self.assertEqual(proxy.uninhibit_call, ("Uninhibit", "(u)", 42))

    def test_freedesktop_fallback_for_both_modes(self):
        for mode in (inhibit.InhibitStrings.IDLE, inhibit.InhibitStrings.SUSPEND):
            proxy = FakeProxy()
            calls = []

            def get_proxy(dbus, calls=calls, proxy=proxy):
                calls.append(dbus)
                if dbus == self.plugin.GNOME_DBUS:
                    raise GLib.Error("GNOME session manager unavailable")
                return proxy

            self.plugin._SessionInhibit__get_dbus_proxy = get_proxy
            config.set("plugins", self.plugin.CONFIG_MODE, mode)

            self.plugin.plugin_on_unpaused()

            self.assertEqual(
                calls,
                [self.plugin.GNOME_DBUS, self.plugin.FREEDESKTOP_DBUS[mode]],
            )
            self.assertEqual(
                proxy.inhibit_call,
                (
                    "(ss)",
                    (self.plugin.APPLICATION_ID, self.plugin.INHIBIT_REASON),
                ),
            )

            self.plugin.plugin_on_paused()
            self.assertEqual(proxy.uninhibit_call, ("UnInhibit", "(u)", 42))
