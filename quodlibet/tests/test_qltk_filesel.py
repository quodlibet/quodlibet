from tests import TestCase

import os
import sys
sys.modules['dircache'] = os # cheat the dircache effects

from quodlibet.qltk.filesel import DirectoryTree, FileSelector
from quodlibet.qltk.filesel import MainDirectoryTree, MainFileSelector
from quodlibet import const
import quodlibet.config


class TDirectoryTree(TestCase):

    if os.name == "nt":
        ROOTS = [const.HOME, "C:\\"]
    else:
        ROOTS = [const.HOME, "/"]

    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()

    def test_initial(self):
        paths = ["/", const.HOME, "/usr/bin"]
        if os.name == "nt":
            paths = ["C:\\", const.HOME]

        for path in paths:
            dirlist = DirectoryTree(path, folders=self.ROOTS)
            model, rows = dirlist.get_selection().get_selected_rows()
            selected = [model[row][0] for row in rows]
            dirlist.destroy()
            self.failUnlessEqual([path], selected)

    def test_bad_initial(self):
        invalid = os.path.join("bin", "file", "does", "not", "exist")
        for path in self.ROOTS:
            newpath = os.path.join(path, invalid)
            dirlist = DirectoryTree(newpath, folders=self.ROOTS)
            selected = dirlist.get_selected_paths()
            dirlist.destroy()
            # select the last valid parent directory
            self.assertEqual(len(selected), 1)
            self.assertTrue(selected[0].startswith(path))

    def test_bad_go_to(self):
        newpath = "/woooooo/bar/fun/broken"
        dirlist = DirectoryTree("/", folders=self.ROOTS)
        dirlist.go_to(newpath)
        dirlist.destroy()

    def test_main(self):
        main = MainDirectoryTree(folders=["/"])
        self.assertTrue(len(main.get_model()))

        main = MainDirectoryTree()
        self.assertTrue(len(main.get_model()))


class TFileSelector(TestCase):

    if os.name == "nt":
        ROOTS = [const.HOME, u"C:\\"]
        INITIAL = u"C:\\"
        # XXX: create a testing file hierarchy in tmp instead
        PATHS = [os.path.join(INITIAL, p) for p in os.listdir(INITIAL)[:2]]
    else:
        ROOTS = [const.HOME, "/"]
        INITIAL = "/dev"
        PATHS = ["/dev/null", "/dev/zero"]

    def setUp(self):
        quodlibet.config.init()
        self.fs = FileSelector(
            initial=self.INITIAL, filter=(lambda s: s in self.PATHS),
            folders=self.ROOTS)
        self.fs.connect('changed', self._changed)
        self.files = None
        self.fs.rescan()

    def tearDown(self):
        self.fs.destroy()
        quodlibet.config.quit()

    def _changed(self, fs, selection):
        self.selection = selection
        self.files = fs.get_selected_paths()
        self.files.sort()

    def test_select(self):
        expected = self.PATHS
        expected.sort()

        self.selection.select_all()
        self.assertEqual(self.files, expected)

    def test_select_rescan(self):
        expected = self.PATHS
        expected.sort()

        self.selection.select_all()
        self.assertEqual(self.files, expected)

        files_prev = self.fs.get_selected_paths()
        self.fs.rescan()
        self.assertEqual(self.files, expected)
        self.assertEqual(self.files, files_prev)

    def test_main(self):
        MainFileSelector()
