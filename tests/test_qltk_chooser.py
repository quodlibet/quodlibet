# Copyright 2017 Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os

from gi.repository import Gtk
from senf import fsnative

from quodlibet.qltk.chooser import (
    choose_files,
    get_current_dir,
    set_current_dir,
    choose_folders,
    create_chooser_filter,
    choose_target_file,
    choose_target_folder,
    with_response,
)
from quodlibet.util import is_osx, is_wine

from . import TestCase, skipIf


@skipIf(is_wine(), "hangs under wine")
@skipIf(is_osx(), "crashy on macOS")
class Tchooser(TestCase):
    def test_choose_files(self):
        w = Gtk.Window()
        with with_response(Gtk.ResponseType.CANCEL):
            assert choose_files(w, "title", "action") == []

    def test_choose_folders(self):
        w = Gtk.Window()
        with with_response(Gtk.ResponseType.CANCEL):
            assert choose_folders(w, "title", "action") == []

    def test_choose_filter(self):
        cf = create_chooser_filter("filter", ["*.txt"])
        assert isinstance(cf, Gtk.FileFilter)
        assert cf.get_name() == "filter"

        w = Gtk.Window()
        with with_response(Gtk.ResponseType.CANCEL):
            assert choose_files(w, "title", "action", cf) == []

    def test_choose_target_file(self):
        w = Gtk.Window()
        with with_response(Gtk.ResponseType.CANCEL):
            assert choose_target_file(w, "title", "action") is None
        with with_response(Gtk.ResponseType.CANCEL):
            assert choose_target_file(w, "title", "action", "example") is None

    def test_choose_target_folder(self):
        w = Gtk.Window()
        with with_response(Gtk.ResponseType.CANCEL):
            assert choose_target_folder(w, "title", "action") is None
        with with_response(Gtk.ResponseType.CANCEL):
            assert choose_target_folder(w, "title", "action", "example") is None

    def test_get_current_dir(self):
        path = get_current_dir()
        assert isinstance(path, fsnative)

    def test_set_current_dir(self):
        set_current_dir(fsnative("."))
        assert get_current_dir() == os.getcwd()
