from unittest import TestCase
from tests import registerCase, Mock
import os, gtk
from widgets import DirectoryTree

class TestDirTree(TestCase):
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

registerCase(TestDirTree)

