# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, mkdtemp
from tests.helper import __

import os
import sys

sys.modules["dircache"] = os  # cheat the dircache effects

from quodlibet.fsn import fsnative

from quodlibet.qltk.filesel import (
    DirectoryTree,
    FileSelector,
    get_drives,
    MainDirectoryTree,
    MainFileSelector,
    get_gtk_bookmarks,
    parse_gtk_bookmarks,
)
from quodlibet.util.path import get_home_dir
import quodlibet.config
from quodlibet.util import is_windows


class Tget_gtk_bookmarks(TestCase):
    def test_main(self):
        paths = get_gtk_bookmarks()
        assert all(isinstance(p, fsnative) for p in paths)

    def test_parse(self):
        if is_windows():
            return

        data = (
            b"file:///foo/bar\nfile:///home/user\n"
            b"file:///home/user/Downloads Downloads\n"
        )
        paths = parse_gtk_bookmarks(data)
        assert all(isinstance(p, fsnative) for p in paths)


class TDirectoryTree(TestCase):
    if os.name == "nt":
        ROOTS = [get_home_dir(), "C:\\"]
    else:
        ROOTS = [get_home_dir(), "/"]

    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()

    def test_initial(self):
        if os.name == "nt":
            paths = ["C:\\", get_home_dir()]
        else:
            paths = ["/", get_home_dir()]

        for path in paths:
            dirlist = DirectoryTree(path, folders=self.ROOTS)
            model, rows = dirlist.get_selection().get_selected_rows()
            selected = [model[row][0] for row in rows]
            dirlist.destroy()
            self.assertEqual([os.path.normpath(path)], selected)

    def test_bad_initial(self):
        invalid = os.path.join("bin", "file", "does", "not", "exist")
        for path in self.ROOTS:
            newpath = os.path.join(path, invalid)
            dirlist = DirectoryTree(newpath, folders=self.ROOTS)
            selected = dirlist.get_selected_paths()
            dirlist.destroy()
            # select the last valid parent directory
            self.assertEqual(len(selected), 1)
            assert selected[0].startswith(path)

    def test_bad_go_to(self):
        newpath = "/woooooo/bar/fun/broken"
        dirlist = DirectoryTree("/", folders=self.ROOTS)
        dirlist.go_to(newpath)
        dirlist.destroy()

    def test_main(self):
        folders = ["/"]
        if os.name == "nt":
            folders = ["C:\\"]
        main = MainDirectoryTree(folders=folders)
        assert len(main.get_model())

        main = MainDirectoryTree()
        assert len(main.get_model())

    def test_get_drives(self):
        for path in get_drives():
            assert isinstance(path, fsnative)

    def test_popup(self):
        dt = DirectoryTree(None, folders=self.ROOTS)
        menu = dt._create_menu()
        dt._popup_menu(menu)
        ag = dt._action_group
        # 4 actions: new-folder, delete, refresh, expand
        self.assertEqual(len(list(ag.list_actions())), 4)
        delete_action = ag.lookup_action("delete")
        self.assertIsNotNone(delete_action)
        # Verify the Gio.Menu has the right label for the delete item
        gio_model = menu.gio_model
        delete_label = gio_model.get_item_attribute_value(1, "label").get_string()
        self.assertEqual(delete_label, __("_Delete"))
        assert delete_action.get_enabled()

    def test_multiple_selections(self):
        dt = DirectoryTree(None, folders=self.ROOTS)
        menu = dt._create_menu()
        dt._popup_menu(menu)
        ag = dt._action_group
        gio_model = menu.gio_model
        expand_label = gio_model.get_item_attribute_value(3, "label").get_string()
        assert "sub-folders" in expand_label.lower()
        expand_action = ag.lookup_action("expand")
        assert expand_action.get_enabled()
        sel = dt.get_selection()
        model = dt.get_model()
        for it, _pth in model.iterrows(None):
            sel.select_iter(it)
        dt._popup_menu(menu)
        assert expand_action.get_enabled(), "Select All should work for multiple"
        new_folder_action = ag.lookup_action("new-folder")
        msg = "New Folder should be disabled for multiple"
        assert not new_folder_action.get_enabled(), msg
        assert ag.lookup_action(
            "refresh"
        ).get_enabled(), "Refresh should be enabled for multiple"


class TFileSelector(TestCase):
    def setUp(self):
        quodlibet.config.init()
        self.ROOTS = [mkdtemp(), mkdtemp()]
        self.INITIAL = self.ROOTS[0]
        self.PATHS = [
            os.path.join(self.ROOTS[0], "a"),
            os.path.join(self.ROOTS[0], "b"),
        ]

        for path in self.PATHS:
            open(path, "wb").close()

        self.fs = FileSelector(
            initial=self.INITIAL, filter=(lambda s: s in self.PATHS), folders=self.ROOTS
        )
        self.fs.connect("changed", self._changed)
        self.files = None
        self.fs.rescan()

    def tearDown(self):
        self.fs.destroy()
        quodlibet.config.quit()

        for file_ in self.PATHS:
            os.unlink(file_)
        for dir_ in self.ROOTS:
            os.rmdir(dir_)

    def _changed(self, fs, selection):
        self.selection = selection
        self.files = fs.get_selected_paths()
        self.files.sort()

    def test_select(self):
        expected = self.PATHS
        expected.sort()

        self.selection.select_all()
        self.assertEqual(self.files, expected)

    def test_select_rescan(self):
        expected = self.PATHS
        expected.sort()

        self.selection.select_all()
        self.assertEqual(self.files, expected)

        files_prev = self.fs.get_selected_paths()
        self.fs.rescan()
        self.assertEqual(self.files, expected)
        self.assertEqual(self.files, files_prev)

    def test_main(self):
        MainFileSelector()
