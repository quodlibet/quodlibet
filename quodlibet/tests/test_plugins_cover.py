# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import io
import os
import shutil

from gi.repository import Gtk
from gi.repository import GdkPixbuf

from tests import TestCase, mkdtemp, mkstemp, get_data_path

from quodlibet import config
from quodlibet.plugins import Plugin
from quodlibet.formats.mp3 import MP3File
from quodlibet.formats import AudioFile, EmbeddedImage
from quodlibet.plugins.cover import CoverSourcePlugin
from quodlibet.util.cover.manager import CoverPluginHandler, CoverManager
from quodlibet.util.path import path_equal

from .helper import get_temp_copy


DUMMY_COVER = io.StringIO()


class DummyCoverSource1(CoverSourcePlugin):
    @staticmethod
    def priority():
        return 0.95

    @property
    def cover(self):
        DummyCoverSource1.cover_call = True
        return None


class DummyCoverSource2(CoverSourcePlugin):
    @staticmethod
    def priority():
        return 0.5

    @property
    def cover(self):
        DummyCoverSource2.cover_call = True
        return DUMMY_COVER

    def fetch_cover(self):
        DummyCoverSource2.fetch_call = True
        return self.emit('fetch-success', self.cover)


class DummyCoverSource3(CoverSourcePlugin):
    @staticmethod
    def priority():
        return 0.3

    @property
    def cover(self):
        DummyCoverSource3.cover_call = True
        return None

    def fetch_cover(self):
        DummyCoverSource3.fetch_call = True
        return self.emit('fetch-success', DUMMY_COVER)

dummy_sources = [Plugin(s) for s in
    [DummyCoverSource1, DummyCoverSource2, DummyCoverSource3]
]


class TCoverManager(TestCase):
    built_in_count = 2

    def setUp(self):
        self.manager = CoverManager()

    def test_has_builtin_covers(self):
        self.assertEqual(len(list(self.manager.sources)), self.built_in_count)
        manager = CoverPluginHandler(use_built_in=False)
        self.assertEqual(len(list(manager.sources)), 0)

    def test_only_enabled(self):
        for source in dummy_sources:
            self.manager.plugin_handler.plugin_handle(source)
        self.assertEqual(len(list(self.manager.sources)), self.built_in_count)
        for source in dummy_sources:
            self.manager.plugin_handler.plugin_enable(source)
        self.assertEqual(len(list(self.manager.sources)),
                         self.built_in_count + len(dummy_sources))
        for k, source in enumerate(dummy_sources):
            self.manager.plugin_handler.plugin_disable(source)
            self.assertEqual(len(list(self.manager.sources)),
                             self.built_in_count + len(dummy_sources) - k - 1)

    def test_sources_sorted(self):
        for source in dummy_sources:
            self.manager.plugin_handler.plugin_handle(source)
            self.manager.plugin_handler.plugin_enable(source)
        priorities = [p.priority() for p in self.manager.sources]
        self.assertSequenceEqual(priorities, sorted(priorities, reverse=True))
        # Test that sources are sorted even after removing some of the sources
        for source in dummy_sources:
            self.manager.plugin_handler.plugin_disable(source)
            ps = [p.priority() for p in self.manager.sources]
            self.assertSequenceEqual(ps, sorted(ps, reverse=True))

    def test_acquire_cover_sync(self):
        song = AudioFile({"~filename": "/dev/null"})

        manager = CoverManager(use_built_in=False)
        handler = manager.plugin_handler
        for source in dummy_sources:
            handler.plugin_handle(source)
        handler.plugin_enable(dummy_sources[0])
        self.assertIs(manager.acquire_cover_sync(song), None)
        handler.plugin_enable(dummy_sources[1])
        self.assertIs(manager.acquire_cover_sync(song), DUMMY_COVER)
        handler.plugin_enable(dummy_sources[2])
        self.assertIs(manager.acquire_cover_sync(song), DUMMY_COVER)
        handler.plugin_disable(dummy_sources[1])
        self.assertIs(manager.acquire_cover_sync(song), None)

    def test_acquire_cover(self):
        manager = CoverManager(use_built_in=False)
        handler = manager.plugin_handler
        for source in dummy_sources:
            handler.plugin_handle(source)
        handler.plugin_enable(dummy_sources[0])
        found = []
        result = []

        def done(_found, _result):
            found.append(_found)
            result.append(_result)
        manager.acquire_cover(done, None, None)
        self.runLoop()
        self.assertFalse(found[0])
        handler.plugin_enable(dummy_sources[1])
        manager.acquire_cover(done, None, None)
        self.runLoop()
        self.assertTrue(found[1])
        self.assertIs(result[1], DUMMY_COVER)
        handler.plugin_disable(dummy_sources[1])
        handler.plugin_enable(dummy_sources[2])
        manager.acquire_cover(done, None, None)
        self.runLoop()
        self.assertTrue(found[2])
        self.assertIs(result[2], DUMMY_COVER)

    def test_acquire_cover_calls(self):
        # * fetch_cover shouldn't get called if source provides the cover
        #   synchronously
        # * First cover source should fail providing the cover both
        #   synchronously and asynchronously and only then the next source
        #   should be used
        manager = CoverManager(use_built_in=False)
        handler = manager.plugin_handler
        found = []
        result = []
        for source in dummy_sources:
            handler.plugin_handle(source)
            handler.plugin_enable(source)
            source.cls.cover_call = False
            source.cls.fetch_call = False

        def done(_found, _result):
            found.append(_found)
            result.append(_result)
        manager.acquire_cover(done, None, None)
        self.runLoop()
        self.assertTrue(found[0])
        self.assertIs(result[0], DUMMY_COVER)
        self.assertTrue(dummy_sources[0].cls.cover_call)
        self.assertTrue(dummy_sources[1].cls.cover_call)
        self.assertFalse(dummy_sources[2].cls.cover_call)
        self.assertFalse(dummy_sources[0].cls.fetch_call)
        self.assertFalse(dummy_sources[1].cls.fetch_call)
        self.assertFalse(dummy_sources[2].cls.fetch_call)
        for source in dummy_sources:
            source.cls.cover_call = False
            source.cls.fetch_call = False
        handler.plugin_disable(dummy_sources[1])
        manager.acquire_cover(done, None, None)
        self.runLoop()
        self.assertTrue(found[1])
        self.assertIs(result[1], DUMMY_COVER)
        self.assertTrue(dummy_sources[0].cls.cover_call)
        self.assertFalse(dummy_sources[1].cls.cover_call)
        self.assertTrue(dummy_sources[2].cls.cover_call)
        self.assertFalse(dummy_sources[0].cls.fetch_call)
        self.assertFalse(dummy_sources[1].cls.fetch_call)
        self.assertTrue(dummy_sources[2].cls.fetch_call)

    def runLoop(self):
        while Gtk.events_pending():
            Gtk.main_iteration()

    def tearDown(self):
        pass


class TCoverManagerBuiltin(TestCase):

    def setUp(self):
        config.init()

        self.main = mkdtemp()

        self.dir1 = mkdtemp(dir=self.main)
        self.dir2 = mkdtemp(dir=self.main)

        h, self.cover1 = mkstemp(".png", dir=self.main)
        os.close(h)
        pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 10, 10)
        pb.savev(self.cover1, "png", [], [])

        h, self.cover2 = mkstemp(".png", dir=self.main)
        os.close(h)
        pb = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, 20, 20)
        pb.savev(self.cover2, "png", [], [])

        self.file1 = get_temp_copy(get_data_path('silence-44-s.mp3'))
        self.file2 = get_temp_copy(get_data_path('silence-44-s.mp3'))

        self.manager = CoverManager()

    def tearDown(self):
        shutil.rmtree(self.main)
        config.quit()

    def test_connect_cover_changed(self):

        called_with = []

        def sig_handler(*args):
            called_with.extend(args)

        obj = object()
        self.manager.connect("cover-changed", sig_handler)
        self.manager.cover_changed([obj])

        self.assertEqual(called_with, [self.manager, [obj]])

    def test_get_primary_image(self):
        self.assertFalse(MP3File(self.file1).has_images)
        self.assertFalse(MP3File(self.file1).has_images)

    def test_manager(self):
        self.assertEqual(len(list(self.manager.sources)), 2)

    def test_main(self):
        # embedd one cover, move one to the other dir
        MP3File(self.file1).set_image(EmbeddedImage.from_path(self.cover1))
        os.unlink(self.cover1)
        dest = os.path.join(self.dir2, "cover.png")
        shutil.move(self.cover2, dest)
        self.cover2 = dest

        # move one audio file in each dir
        shutil.move(self.file1, self.dir1)
        self.file1 = os.path.join(self.dir1, os.path.basename(self.file1))
        shutil.move(self.file2, self.dir2)
        self.file2 = os.path.join(self.dir2, os.path.basename(self.file2))

        song1 = MP3File(self.file1)
        song2 = MP3File(self.file2)

        def is_embedded(fileobj):
            return not path_equal(fileobj.name, self.cover2, True)

        # each should find a cover
        self.assertTrue(is_embedded(self.manager.get_cover(song1)))
        self.assertTrue(not is_embedded(self.manager.get_cover(song2)))

        # both settings should search both songs before giving up
        config.set("albumart", "prefer_embedded", True)
        self.assertTrue(
            is_embedded(self.manager.get_cover_many([song1, song2])))
        self.assertTrue(
            is_embedded(self.manager.get_cover_many([song2, song1])))

        config.set("albumart", "prefer_embedded", False)
        self.assertTrue(
            not is_embedded(self.manager.get_cover_many([song1, song2])))
        self.assertTrue(
            not is_embedded(self.manager.get_cover_many([song2, song1])))
