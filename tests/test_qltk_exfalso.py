# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from unittest.mock import Mock, patch

from gi.repository import Gtk

from quodlibet.qltk import exfalsowindow
from quodlibet.qltk.msg import CancelRevertSave
from tests import TestCase

from quodlibet.qltk.exfalsowindow import ExFalsoWindow
from quodlibet.library import SongLibrary
import quodlibet.config


class TExFalsoWindow(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.ef = ExFalsoWindow(SongLibrary())

    def test_nothing(self):
        assert self.ef.get_child()

    def tearDown(self):
        self.ef.destroy()
        quodlibet.config.quit()

    def test_prefs(self):
        self.prefs = exfalsowindow.PreferencesWindow(None)
        self.prefs.present()
        assert self.prefs.get_title() == "Ex Falso Preferences"
        assert self.prefs.get_child(), "No window contents"
        nb = self.prefs.get_child()
        pages = [type(nb.get_nth_page(i)) for i in range(nb.get_n_pages())]
        assert pages == [self.prefs.Tagging], "Wrong prefs pages"
        self.prefs.destroy()

    def _newest_file_list_controller(self, cls):
        view = self.ef._fs.get_end_child().get_child()
        return [c for c in view.observe_controllers() if type(c) is cls][0]

    def test_clicking_file_list_with_pending_edits_offers_save(self):
        save = Mock()
        self.ef.set_pending(save)
        click = self._newest_file_list_controller(Gtk.GestureClick)
        with patch.object(CancelRevertSave, "run", return_value=Gtk.ResponseType.YES):
            click.emit("pressed", 1, 0, 0)
        save.emit.assert_called_once_with("clicked")

    def test_focusing_file_list_with_pending_edits_offers_save(self):
        save = Mock()
        self.ef.set_pending(save)
        focus = self._newest_file_list_controller(Gtk.EventControllerFocus)
        with patch.object(CancelRevertSave, "run", return_value=Gtk.ResponseType.YES):
            focus.emit("enter")
        save.emit.assert_called_once_with("clicked")
