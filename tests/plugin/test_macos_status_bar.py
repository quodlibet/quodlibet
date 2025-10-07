# Copyright 2025 Umiko
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import unittest
from tests.plugin import PluginTestCase

PLUGIN_ID = "macos_status_bar"

class TestMacOSStatusBar(PluginTestCase):
    """
    Minimal testing for the MacOS Status bar plugin (using existing PluginTestCase)
    - For most "in-depth" tests,
    it would require us to import AppKit (i.e. run the tests on a MacOS)
    - This still verifies that the plugin is recognized and discoverable
    and that the device is a MacOS device
    """

    def _plugin_class(self):
        mod = self.modules[PLUGIN_ID]
        return mod.MacOSStatusBarPlugin

    def test_plugin_is_discoverable(self):
        """
        Just make sure the plugin exists
        """
        self.assertIn(PLUGIN_ID, self.plugins)

        cls = self._plugin_class()
        self.assertTrue(hasattr(cls, "PLUGIN_NAME") and cls.PLUGIN_NAME.strip())
        self.assertTrue(hasattr(cls, "PLUGIN_DESC") and cls.PLUGIN_DESC.strip())
        self.assertTrue(hasattr(cls, "VERSION") and cls.VERSION.strip())
        self.assertEqual(cls.PLUGIN_ID, PLUGIN_ID)

    def test_plugin_id_unique(self):
        """
        This should be the only plugin with this ID
        """
        ids = list(self.plugins.keys())
        self.assertEqual(ids.count(PLUGIN_ID), 1, "PLUGIN_ID must be unique")

    def test_no_cocoa_off_macos(self):
        """
        The plugin should only be enabled on MacOS
        (even if the user checks it in the interface)
        """
        # Linux
        prev = sys.platform

        try:
            sys.platform = "linux"
            plugin = self._plugin_class()()

            # Since we already have a check within the plugin
            # the main reason for this is to make sure Apple Cocoa
            # doesn't cause issues on other platforms
            self.assertIsNone(
                getattr(plugin, "_cocoa", None),
                "Plugin should not create Cocoa controller"
                "on any other platform (Linux)",
            )
        finally:
            sys.platform = prev

        # Windows
        prev = sys.platform

        try:
            sys.platform = "win32"
            plugin = self._plugin_class()()

            self.assertIsNone(
                getattr(plugin, "_cocoa", None),
                "Plugin should not create Cocoa controller"
                "on any other platform (Windows)",
            )
        finally:
            sys.platform = prev

    @unittest.skipUnless(sys.platform == "darwin", "Check if running on MacOS")
    def test_macos_enable_and_disable_once(self):
        """
        We don't want to explicitly fail if running on something other than MacOS
        """
        try:
            import objc # noqa
            from AppKit import NSApplication # noqa
        except Exception:
            self.skipTest("PyObjC/AppKit not available in this environment")

        plugin = self._plugin_class()()
        is_enabled = plugin.enabled()

        self.assertTrue(is_enabled, "Plugin should be enabled")

        ctrl = getattr(plugin, "_cocoa", None)
        self.assertIsNotNone(ctrl, "StatusBarController should be initialized")
        self.assertTrue(hasattr(ctrl, "status_bar_view"))
        self.assertTrue(hasattr(ctrl, "tick_") and callable(ctrl.tick_))

        plugin.disabled()
        self.assertIsNone(
            getattr(plugin, "_cocoa", None), "disabled() should clear _cocoa"
        )
