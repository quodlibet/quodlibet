from gi.repository import Gtk

from tests import TestCase, add

from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.delete import DeleteDialog, TrashDialog

SONG = AudioFile({"~filename": "/dev/null"})
SONG.sanitize()


class TDeleteDialog(TestCase):
    def test_delete(self):
        dialog = DeleteDialog(None, [])
        dialog.destroy()

    def test_trash(self):
        dialog = TrashDialog(None, [])
        dialog.destroy()

    def test_delete_full(self):
        w = Gtk.Window()
        dialog = DeleteDialog(w, [SONG])
        dialog.destroy()

    def test_trash_full(self):
        w = Gtk.Window()
        dialog = TrashDialog(w, [SONG])
        dialog.destroy()

add(TDeleteDialog)
