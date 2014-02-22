from gi.repository import Gtk

from tests import TestCase

from quodlibet.formats._audio import AudioFile
from quodlibet.qltk.delete import DeleteDialog, TrashDialog, TrashMenuItem

SONG = AudioFile({"~filename": "/dev/null"})
SONG.sanitize()


class TDeleteDialog(TestCase):
    def test_delete_songs(self):
        dialog = DeleteDialog.for_songs(None, [])
        dialog.destroy()

    def test_delete_files(self):
        dialog = DeleteDialog.for_files(None, [])
        dialog.destroy()

    def test_trash_songs(self):
        dialog = TrashDialog.for_songs(None, [])
        dialog.destroy()

    def test_trash_files(self):
        dialog = TrashDialog.for_files(None, [])
        dialog.destroy()

    def test_delete_songs_full(self):
        w = Gtk.Window()
        dialog = DeleteDialog.for_songs(w, [SONG])
        dialog.destroy()

    def test_delete_files_full(self):
        w = Gtk.Window()
        dialog = DeleteDialog.for_files(w, [SONG("~filename")])
        dialog.destroy()

    def test_trash_songs_full(self):
        w = Gtk.Window()
        dialog = TrashDialog.for_songs(w, [SONG])
        dialog.destroy()

    def test_trash_files_full(self):
        w = Gtk.Window()
        dialog = TrashDialog.for_files(w, [SONG("~filename")])
        dialog.destroy()

    def test_menu_item(self):
        TrashMenuItem().destroy()
