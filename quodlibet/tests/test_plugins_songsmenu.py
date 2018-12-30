# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import shutil

from quodlibet.library import SongLibrary
from quodlibet.plugins.songsmenu import SongsMenuPlugin
from quodlibet.plugins.songshelpers import any_song, each_song
from tests import TestCase, mkstemp, mkdtemp

import os

from quodlibet.formats import AudioFile
from quodlibet.plugins import PluginManager, Plugin
from quodlibet.qltk.songsmenu import SongsMenuPluginHandler
from tests.helper import capture_output
from tests.test_library_libraries import FakeSong


class TSongsMenuPlugins(TestCase):

    def _confirmer(self, *args):
        self.confirmed = True

    def setUp(self):
        self.tempdir = mkdtemp()
        self.pm = PluginManager(folders=[self.tempdir])
        self.confirmed = False
        self.handler = SongsMenuPluginHandler(self._confirmer, self._confirmer)
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
                "from quodlibet.plugins.songsmenu import SongsMenuPlugin\n")
            file.write("class %s(SongsMenuPlugin):\n" % name)
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
                           "*args); raise Exception(\"as expected\")\n"
                           % (indent, f, name))
            else:
                file.write("%sdef %s(*args): return args\n" % (indent, f))
        file.flush()
        file.close()

    def test_empty_has_no_plugins(self):
        self.pm.rescan()
        self.assertEquals(self.pm.plugins, [])

    def test_name_and_desc_plus_func_is_one(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 1)

    def test_additional_functions_still_only_one(self):
        self.create_plugin(name='Name', desc='Desc',
                funcs=['plugin_song', 'plugin_songs'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 1)

    def test_two_plugins_are_two(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.create_plugin(name='Name2', desc='Desc2',
                funcs=['plugin_albums'])
        self.pm.rescan()
        self.assertEquals(len(self.pm.plugins), 2)

    def test_disables_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        self.failIf(self.pm.enabled(self.pm.plugins[0]))

    def test_enabledisable_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        plug = self.pm.plugins[0]
        self.pm.enable(plug, True)
        self.failUnless(self.pm.enabled(plug))
        self.pm.enable(plug, False)
        self.failIf(self.pm.enabled(plug))

    def test_ignores_broken_plugin(self):
        self.create_plugin(name="Broken", desc="Desc",
                           funcs=["__init__", "plugin_song"])
        self.pm.rescan()
        plug = self.pm.plugins[0]
        self.pm.enable(plug, True)
        with capture_output():
            menu = self.handler.Menu(None, [AudioFile()])
        self.failIf(menu and menu.get_children())

    def test_Menu(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.handler.Menu(None, [AudioFile()])

    def test_handling_songs_without_confirmation(self):
        plugin = Plugin(FakeSongsMenuPlugin)
        self.handler.plugin_enable(plugin)
        MAX = FakeSongsMenuPlugin.MAX_INVOCATIONS
        songs = [AudioFile({'~filename': "/tmp/%s" % x, 'artist': 'foo'})
                 for x in range(MAX)]
        self.handler.handle(plugin.id, self.library, None, songs)
        self.failIf(self.confirmed, ("Wasn't expecting a confirmation for %d"
                                     " invocations" % len(songs)))

    def test_handling_lots_of_songs_with_confirmation(self):
        plugin = Plugin(FakeSongsMenuPlugin)
        self.handler.plugin_enable(plugin)
        MAX = FakeSongsMenuPlugin.MAX_INVOCATIONS
        songs = [AudioFile({'~filename': "/tmp/%s" % x, 'artist': 'foo'})
                 for x in range(MAX + 1)]
        self.handler.handle(plugin.id, self.library, None, songs)
        self.failUnless(self.confirmed,
                        ("Should have confirmed %d invocations (Max=%d)."
                         % (len(songs), MAX)))


def even(i):
    return i % 2 == 0


def never(_):
    return False


class Tsongsmenu(TestCase):
    songs = [FakeSong(1), FakeSong(2)]

    def test_any_song(self):
        FakeSongsMenuPlugin.plugin_handles = any_song(even)
        p = FakeSongsMenuPlugin(self.songs, None)
        self.failUnless(p.plugin_handles(self.songs))
        self.failIf(p.plugin_handles(self.songs[:1]))

    def test_any_song_multiple(self):
        FakeSongsMenuPlugin.plugin_handles = any_song(even, never)
        p = FakeSongsMenuPlugin(self.songs, None)
        self.failIf(p.plugin_handles(self.songs))
        self.failIf(p.plugin_handles(self.songs[:1]))

    def test_each_song(self):
        FakeSongsMenuPlugin.plugin_handles = each_song(even)
        p = FakeSongsMenuPlugin(self.songs, None)
        self.failIf(p.plugin_handles(self.songs))
        self.failUnless(p.plugin_handles(self.songs[1:]))

    def test_each_song_multiple(self):
        FakeSongsMenuPlugin.plugin_handles = each_song(even, never)
        p = FakeSongsMenuPlugin(self.songs, None)
        self.failIf(p.plugin_handles(self.songs))
        self.failIf(p.plugin_handles(self.songs[:1]))


class FakeSongsMenuPlugin(SongsMenuPlugin):
    PLUGIN_NAME = "Fake Songs Menu Plugin"
    PLUGIN_ID = "SongsMunger"
    MAX_INVOCATIONS = 50

    def __init__(self, songs, library):
        super(FakeSongsMenuPlugin, self).__init__(songs, library)
        self.total = 0

    def plugin_song(self, song):
        self.total += 1
        if self.total > self.MAX_INVOCATIONS:
            raise ValueError("Shouldn't have called me on this many songs"
                             " (%d > %d)" % (self.total,
                                             self.MAX_INVOCATIONS))
