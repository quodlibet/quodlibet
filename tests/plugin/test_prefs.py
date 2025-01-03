# Copyright 2012 Christoph Reiter
#           2020 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import Gtk
from pytest import fixture

from quodlibet import config, app
from quodlibet.ext._shared.squeezebox.server import SqueezeboxError
from quodlibet.plugins import Plugin
from tests.plugin import init_fake_app, destroy_fake_app, plugins

PREFS_PLUGINS = [p for p in plugins.values() if hasattr(p.cls, "PluginPreferences")]


@fixture
def fake_app():
    config.init()
    init_fake_app()
    yield app
    destroy_fake_app()
    config.quit()


@fixture(params=PREFS_PLUGINS, ids=lambda p: p.cls)
def plugin_with_prefs(fake_app, request) -> Plugin:
    return request.param


class TestPluginPrefs:
    def test_prefs_detected(self):
        assert PREFS_PLUGINS, "No plugins with preferences detected"

    def test_plugin_pref(self, plugin_with_prefs):
        plugin = plugin_with_prefs.cls
        if hasattr(plugin, "PLUGIN_INSTANCE"):
            plugin = plugin()
        try:
            plugin.PluginPreferences(Gtk.Window())
        except SqueezeboxError:
            # TODO: fix squeezebox init errors where config exists
            pass
