from tests import TestCase, add

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
        for path in self.ROOTS:
            newpath = os.path.join(path, "bin/file/does/not/exist")
            dirlist = DirectoryTree(newpath, folders=self.ROOTS)
            selected = dirlist.get_selected_paths()
            dirlist.destroy()
            self.failUnlessEqual([path], selected)

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

add(TDirectoryTree)


class TFileSelector(TestCase):

    ROOTS = [const.HOME, "/"]

    def setUp(self):
        quodlibet.config.init()
        self.fs = FileSelector(
            initial="/dev", filter=(lambda s: s in ["/dev/null", "/dev/zero"]),
            folders=self.ROOTS)
        self.fs.connect('changed', self.changed)
        self.expected = []
        self.fs.rescan()

    def tearDown(self):
        self.fs.destroy()
        quodlibet.config.quit()

    def changed(self, fs, selection):
        self.selection = selection
        files = fs.get_selected_paths()
        files.sort()
        self.expected.sort()
        self.assertEqual(files, self.expected)
        self.expected = None

    def test_select(self):
        self.expected = ["/dev/null", "/dev/zero"]
        self.selection.select_all()
        self.failUnless(self.expected is None)

    def test_select_rescan(self):
        all_ = ["/dev/null", "/dev/zero"]
        self.expected = all_
        self.selection.select_all()
        files = self.fs.get_selected_paths()
        self.expected = all_
        self.fs.rescan()
        self.assertEqual(files, self.fs.get_selected_paths())

    def test_main(self):
        MainFileSelector()

add(TFileSelector)
