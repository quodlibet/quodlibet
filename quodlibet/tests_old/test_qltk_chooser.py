from tests import TestCase, add

import os

from quodlibet.qltk.chooser import FolderChooser, FileChooser

class TFolderChooser(TestCase):
    Kind = FolderChooser
    def test_init_nodir(self):
        f = self.Kind(None, "A file chooser")
        f.destroy()

    def test_init_dir(self):
        f = self.Kind(None, "A file chooser", initial_dir="/home")
        f.destroy()
add(TFolderChooser)

class TFileChooser(TFolderChooser):
    Kind = FileChooser
add(TFileChooser)
