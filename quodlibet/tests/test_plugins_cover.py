import io

from gi.repository import Gtk

from tests import TestCase, add

from quodlibet.plugins import Plugin
from quodlibet.plugins.cover import CoverSourcePlugin
from quodlibet.util.cover.manager import CoverPluginHandler

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
        self.manager = CoverPluginHandler()

    def test_has_builtin_covers(self):
        self.assertEqual(len(list(self.manager.sources)), self.built_in_count)
        manager = CoverPluginHandler(use_built_in=False)
        self.assertEqual(len(list(manager.sources)), 0)

    def test_only_enabled(self):
        for source in dummy_sources:
            self.manager.plugin_handle(source)
        self.assertEqual(len(list(self.manager.sources)), self.built_in_count)
        for source in dummy_sources:
            self.manager.plugin_enable(source)
        self.assertEqual(len(list(self.manager.sources)),
                         self.built_in_count + len(dummy_sources))
        for k, source in enumerate(dummy_sources):
            self.manager.plugin_disable(source)
            self.assertEqual(len(list(self.manager.sources)),
                             self.built_in_count + len(dummy_sources) - k - 1)

    def test_sources_sorted(self):
        for source in dummy_sources:
            self.manager.plugin_handle(source)
            self.manager.plugin_enable(source)
        priorities = [p.priority() for p in self.manager.sources]
        self.assertSequenceEqual(priorities, sorted(priorities, reverse=True))
        # Test that sources are sorted even after removing some of the sources
        for source in dummy_sources:
            self.manager.plugin_disable(source)
            ps = [p.priority() for p in self.manager.sources]
            self.assertSequenceEqual(ps, sorted(ps, reverse=True))

    def test_acquire_cover_sync(self):
        manager = CoverPluginHandler(use_built_in=False)
        for source in dummy_sources:
            manager.plugin_handle(source)
        manager.plugin_enable(dummy_sources[0])
        self.assertIs(manager.acquire_cover_sync(None), None)
        manager.plugin_enable(dummy_sources[1])
        self.assertIs(manager.acquire_cover_sync(None), DUMMY_COVER)
        manager.plugin_enable(dummy_sources[2])
        self.assertIs(manager.acquire_cover_sync(None), DUMMY_COVER)
        manager.plugin_disable(dummy_sources[1])
        self.assertIs(manager.acquire_cover_sync(None), None)

    def test_acquire_cover(self):
        manager = CoverPluginHandler(use_built_in=False)
        for source in dummy_sources:
            manager.plugin_handle(source)
        manager.plugin_enable(dummy_sources[0])
        found = []
        result = []
        def done(_found, _result):
            found.append(_found)
            result.append(_result)
        manager.acquire_cover(done, None, None)
        self.runLoop()
        self.assertFalse(found[0])
        manager.plugin_enable(dummy_sources[1])
        manager.acquire_cover(done, None, None)
        self.runLoop()
        self.assertTrue(found[1])
        self.assertIs(result[1], DUMMY_COVER)
        manager.plugin_disable(dummy_sources[1])
        manager.plugin_enable(dummy_sources[2])
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
        manager = CoverPluginHandler(use_built_in=False)
        found = []
        result = []
        for source in dummy_sources:
            manager.plugin_handle(source)
            manager.plugin_enable(source)
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
        manager.plugin_disable(dummy_sources[1])
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

add(TCoverManager)
