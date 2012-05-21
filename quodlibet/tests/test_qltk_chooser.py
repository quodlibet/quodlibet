from tests import TestCase, add

from quodlibet.qltk.chooser import FolderChooser, FileChooser
import quodlibet.config

class TFolderChooser(TestCase):
    Kind = FolderChooser
    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()

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
