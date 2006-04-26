import os
import sys
sys.modules['dircache'] = os # cheat the dircache effects
from tests import TestCase, add
from qltk.filesel import DirectoryTree, FileSelector

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
