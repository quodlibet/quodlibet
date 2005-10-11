import os, sys
sys.modules['dircache'] = os # cheat the dircache effects
from tempfile import mkstemp, mkdtemp

from tests import TestCase, add
from efwidgets import DirectoryTree, EFPluginManager, FileSelector, ExFalsoWindow
from tests.test_plugins import TPluginManager

class TDirectoryTree(TestCase):
    def test_initial(self):
        for path in ["/", "/home", os.environ["HOME"], "/usr/bin"]:
            dirlist = DirectoryTree(path)
            model, rows = dirlist.get_selection().get_selected_rows()
            selected = [model[row][0] for row in rows]
            dirlist.destroy()
            self.failUnlessEqual([path], selected)

    def test_bad_initial(self):
        for path in ["/", os.environ["HOME"]]:
            newpath = os.path.join(path, "bin/file/does/not/exist")
            dirlist = DirectoryTree(newpath)
            model, rows = dirlist.get_selection().get_selected_rows()
            selected = [model[row][0] for row in rows]
            dirlist.destroy()
            self.failUnlessEqual([path], selected)

    def test_bad_go_to(self):
         newpath = "/woooooo/bar/fun/broken"
         dirlist = DirectoryTree("/")
         dirlist.go_to(newpath)
         dirlist.destroy()

add(TDirectoryTree)

class TEFPluginManager(TPluginManager):
    def setUp(self):
        self.tempdir = mkdtemp()
        self.pm = EFPluginManager(folders=[self.tempdir])
        self.pm.rescan()
        self.assertEquals(self.pm.list(), [])

    def test_disables_plugin(self): pass

    def test_enables_plugin(self):
        self.create_plugin(name='Name', desc='Desc', funcs=['plugin_song'])
        self.pm.rescan()
        self.failUnless(self.pm.enabled(self.pm.list()[0]))

add(TEFPluginManager)

class TFileSelector(TestCase):
    def setUp(self):
        self.fs = FileSelector(
            initial="/dev", filter=(lambda s: s in ["null", "zero"]))
        self.fs.connect('changed', self.changed)
        self.expected = []
        self.fs.rescan()

    def changed(self, fs, selection):
        self.selection = selection
        model, rows = selection.get_selected_rows()
        files = [model[row][0] for row in rows]
        files.sort()
        self.expected.sort()
        self.assertEqual(files, self.expected)
        self.expected = None

    def test_select(self):
        self.expected = ["/dev/null", "/dev/zero"]
        self.selection.select_all()
        self.failUnless(self.expected is None)

    def tearDown(self):
        self.fs.destroy()
add(TFileSelector)

class TExFalsoWindow(TestCase):
    def setUp(self):
        from qltk import SongWatcher
        self.ef = ExFalsoWindow(SongWatcher())

    def test_nothing(self):
        self.failUnless(self.ef.child)

    def tearDown(self):
        self.ef.destroy()
add(TExFalsoWindow)
