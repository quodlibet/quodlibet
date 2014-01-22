from tests import TestCase
from tests.helper import realized

from quodlibet import plugins
from quodlibet import config

from quodlibet.plugins import Plugin
from quodlibet.qltk.models import ObjectStore
from quodlibet.qltk.pluginwin import PluginWindow, PluginErrorWindow, \
    PluginListView, PluginFilterCombo, PluginPreferencesContainer, \
    ComboType


class FakePlugin(object):
    PLUGIN_ID = "fo<o"
    PLUGIN_NAME = "b>ar"
    PLUGIN_DESC = "quux"

    @classmethod
    def PluginPreferences(cls, parent):
        return PluginFilterCombo()


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

    def test_filter_combo(self):
        combo = PluginFilterCombo()
        combo.refill(["a", "b", "c"], True)
        self.assertEqual(combo.get_active_tag()[1], ComboType.ALL)
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
