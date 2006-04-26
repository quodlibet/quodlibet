import os
from tests import add, TestCase
from qltk.chooser import FolderChooser, FileChooser

class TFolderChooser(TestCase):
    Kind = FolderChooser
    def test_init_nodir(self):
        f = self.Kind(None, "A file chooser")
        self.assertEqual(f.get_current_folder(), os.path.realpath("."))
        f.destroy()

    def test_init_dir(self):
        f = self.Kind(None, "A file chooser", initial_dir="/home")
        self.assertEqual(f.get_current_folder(), "/home")
        f.destroy()
add(TFolderChooser)

class TFileChooser(TFolderChooser):
    Kind = FileChooser
add(TFileChooser)
