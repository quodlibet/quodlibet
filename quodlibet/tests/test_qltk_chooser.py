from tests import TestCase

from gi.repository import Gtk

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
        while Gtk.events_pending():
            Gtk.main_iteration()
        f.destroy()

    def test_init_dir(self):
        f = self.Kind(None, "A file chooser", initial_dir="/home")
        while Gtk.events_pending():
            Gtk.main_iteration()
        f.destroy()


class TFileChooser(TFolderChooser):
    Kind = FileChooser

    def test_filter(self):
        f = lambda *x: None
        x = FileChooser(None, "foo", filter=f)
        while Gtk.events_pending():
            Gtk.main_iteration()
        x.destroy()
