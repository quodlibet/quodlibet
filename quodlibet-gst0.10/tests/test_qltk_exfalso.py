from tests import TestCase, add
from qltk.exfalso import ExFalsoWindow, EFPluginManager
from tests.test_plugins___init__ import TPluginManager
from qltk.watcher import SongWatcher
from tempfile import mkdtemp

class TEFPluginManager(TPluginManager):
    def setUp(self):
        self.tempdir = mkdtemp()
        self.pm = EFPluginManager(folders=[self.tempdir])
        self.pm.rescan()
        self.assertEquals(self.pm.list(), [])

    def test_disables_plugin(self):
        pass

    def test_enables_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        self.failUnless(self.pm.enabled(self.pm.list()[0]))
add(TEFPluginManager)

class TExFalsoWindow(TestCase):
    def setUp(self):
        self.ef = ExFalsoWindow(SongWatcher())

    def test_nothing(self):
        self.failUnless(self.ef.child)

    def tearDown(self):
        self.ef.destroy()
add(TExFalsoWindow)
