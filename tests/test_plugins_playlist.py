# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

"""TODO: Share better with, i.e. test MenuItemPlugin directly"""

import os
import shutil

from gi.repository import Gtk
from quodlibet.browsers import Browser

from quodlibet.library import SongLibrary
from quodlibet.plugins.playlist import PlaylistPlugin, PlaylistPluginHandler
from quodlibet.util.collection import Playlist
from tests import TestCase, mkstemp, mkdtemp
from quodlibet.plugins import PluginManager, Plugin
from tests.helper import capture_output

MAX_PLAYLISTS = 50
TEST_PLAYLIST = Playlist("foo")


def generate_playlists(n):
    return [Playlist("Playlist %d" % x) for x in range(n)]


class TPlaylistPlugins(TestCase):

    class MockBrowser(Browser):
        def __init__(self):
            super(TPlaylistPlugins.MockBrowser, self).__init__()
            self.activated = False

        def activate(self):
            self.activated = True

        def get_toplevel(self):
            return self

        def is_toplevel(self):
            return True

    def _confirmer(self, *args):
        self.confirmed = True

    def setUp(self):
        self.tempdir = mkdtemp()
        self.pm = PluginManager(folders=[self.tempdir])
        self.confirmed = False
        self.mock_browser = self.MockBrowser()
        self.handler = PlaylistPluginHandler(self._confirmer)
        self.pm.register_handler(self.handler)
        self.pm.rescan()
        self.assertEquals(self.pm.plugins, [])
        self.library = SongLibrary('foo')

    def tearDown(self):
        self.library.destroy()
        self.pm.quit()
        shutil.rmtree(self.tempdir)

    def create_plugin(self, id='', name='', desc='', icon='',
                      funcs=None, mod=False):
        fd, fn = mkstemp(suffix='.py', text=True, dir=self.tempdir)
        file = os.fdopen(fd, 'w')

        if mod:
            indent = ''
        else:
            file.write(
                "from quodlibet.plugins.playlist import PlaylistPlugin\n")
            file.write("class %s(PlaylistPlugin):\n" % name)
            indent = '    '
            file.write("%spass\n" % indent)

        if name:
            file.write("%sPLUGIN_ID = %r\n" % (indent, name))
        if name:
            file.write("%sPLUGIN_NAME = %r\n" % (indent, name))
        if desc:
            file.write("%sPLUGIN_DESC = %r\n" % (indent, desc))
        if icon:
            file.write("%sPLUGIN_ICON = %r\n" % (indent, icon))
        for f in (funcs or []):
            if f in ["__init__"]:
                file.write("%sdef %s(self, *args): super(%s, self).__init__("
                           "*args); raise Exception(\"as expected.\")\n"
                           % (indent, f, name))
            else:
                file.write("%sdef %s(*args): return args\n" % (indent, f))
        file.flush()
        file.close()

    def test_empty_has_no_plugins(self):
        self.pm.rescan()
        self.assertEquals(self.pm.plugins, [])

    def test_name_and_desc_plus_func_is_one(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_playlist'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 1)

    def test_additional_functions_still_only_one(self):
        self.create_plugin(name='Name', desc='Desc',
                           funcs=['plugin_playlist', 'plugin_playlists'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 1)

    def test_two_plugins_are_two(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_playlist'])
        self.create_plugin(name='Name2', desc='Desc2',
                           funcs=['plugin_albums'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 2)

    def test_disables_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_playlist'])
        self.pm.rescan()
        self.failIf(self.pm.enabled(self.pm.plugins[0]))

    def test_enabledisable_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_playlist'])
        self.pm.rescan()
        plug = self.pm.plugins[0]
        self.pm.enable(plug, True)
        self.failUnless(self.pm.enabled(plug))
        self.pm.enable(plug, False)
        self.failIf(self.pm.enabled(plug))

    def test_ignores_broken_plugin(self):
        self.create_plugin(name="Broken", desc="Desc",
                           funcs=["__init__", "plugin_playlist"])

        self.pm.rescan()
        plug = self.pm.plugins[0]
        self.pm.enable(plug, True)
        menu = Gtk.Menu()
        with capture_output():
            self.handler.populate_menu(menu, None, self.mock_browser,
                                       [TEST_PLAYLIST])
        self.failUnlessEqual(len(menu.get_children()), 0,
                             msg="Shouldn't have enabled a broken plugin")

    def test_populate_menu(self):
        plugin = Plugin(FakePlaylistPlugin)
        self.handler.plugin_enable(plugin)
        menu = Gtk.Menu()
        self.handler.populate_menu(menu, None, self.mock_browser,
                                   [TEST_PLAYLIST])
        # Don't forget the separator
        num = len(menu.get_children()) - 1
        self.failUnlessEqual(num, 1, msg="Need 1 plugin not %d" % num)

    def test_handling_playlists_without_confirmation(self):
        plugin = Plugin(FakePlaylistPlugin)
        self.handler.plugin_enable(plugin)
        playlists = generate_playlists(MAX_PLAYLISTS)
        self.handler.handle(plugin.id, self.library, self.mock_browser,
                            playlists)
        self.failUnless("Didn't execute plugin",
                        FakePlaylistPlugin.total > 0)
        self.failIf(self.confirmed, ("Wasn't expecting a confirmation for %d"
                                     " invocations" % len(playlists)))

    def test_handling_lots_of_songs_with_confirmation(self):
        plugin = Plugin(FakePlaylistPlugin)
        self.handler.plugin_enable(plugin)
        playlists = generate_playlists(MAX_PLAYLISTS + 1)
        self.handler.handle(plugin.id, self.library, self.mock_browser,
                            playlists)
        self.failUnless(self.confirmed,
                        ("Should have confirmed %d invocations (Max=%d)."
                         % (len(playlists), MAX_PLAYLISTS)))


class FakePlaylistPlugin(PlaylistPlugin):
    PLUGIN_NAME = "Fake Playlist Plugin"
    PLUGIN_ID = "PlaylistMunger"
    MAX_INVOCATIONS = MAX_PLAYLISTS
    total = 0

    def __init__(self, playlists, library):
        super(FakePlaylistPlugin, self).__init__(playlists, library)
        self.total = 0

    def plugin_playlist(self, _):
        self.total += 1
        if self.total > self.MAX_INVOCATIONS:
            raise ValueError("Shouldn't have called me on this many songs"
                             " (%d > %d)" % (self.total, self.MAX_INVOCATIONS))
