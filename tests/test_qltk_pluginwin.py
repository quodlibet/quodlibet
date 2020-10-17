# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase
from tests.helper import realized

from quodlibet import plugins
from quodlibet import config

from quodlibet.plugins import Plugin
from quodlibet.plugins.cover import CoverSourcePlugin
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk.pluginwin import PluginWindow, PluginErrorWindow, \
    PluginListView, PluginEnabledFilterCombo, PluginPreferencesContainer, \
    EnabledType, PluginTypeFilterCombo


class FakePlugin:
    PLUGIN_ID = "fo<o"
    PLUGIN_NAME = "b>ar"
    PLUGIN_DESC = "quux"

    @classmethod
    def PluginPreferences(cls, parent):
        return PluginEnabledFilterCombo()


class FakePlugin2(FakePlugin):

    @classmethod
    def PluginPreferences(cls, parent):
        return PluginWindow()


PLUGIN = Plugin(FakePlugin)
PLUGIN2 = Plugin(FakePlugin2)


class TPluginWindow(TestCase):
    def setUp(self):
        plugins.init()
        config.init()

    def test_plugin_win(self):
        win = PluginWindow()
        win.destroy()

    def test_plugin_error_window(self):
        win = PluginErrorWindow(None, {"foo": ["bar", "quux"]})
        win.destroy()

    def test_plugin_list(self):
        model = ObjectStore()
        model.append([PLUGIN])
        plist = PluginListView()
        plist.set_model(model)
        with realized(plist):
            plist.select_by_plugin_id("foobar")
        plist.destroy()

    def test_enabled_filter_combo(self):
        combo = PluginEnabledFilterCombo()
        combo.refill(["a", "b", "c"], True)
        self.assertEqual(combo.get_active_row()[1], EnabledType.ALL)
        combo.destroy()

    def test_type_filter_combo(self):
        combo = PluginTypeFilterCombo()
        # The ALL item should be first.
        self.failUnlessEqual(combo.get_active_type(), object)
        # Separator counts as one too
        combo.set_active(1 + 1)
        self.failUnlessEqual(combo.get_active_type(), CoverSourcePlugin)
        combo.destroy()

    def test_plugin_prefs(self):
        cont = PluginPreferencesContainer()
        cont.set_no_plugins()
        cont.set_plugin(PLUGIN)
        cont.set_plugin(None)
        cont.set_plugin(PLUGIN)
        cont.set_plugin(PLUGIN2)

    def tearDown(self):
        plugins.quit()
        config.quit()
