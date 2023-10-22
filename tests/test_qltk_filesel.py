# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, mkdtemp
from tests.helper import __

import os
import sys
sys.modules["dircache"] = os # cheat the dircache effects

from senf import fsnative

from quodlibet.qltk.filesel import DirectoryTree, FileSelector, get_drives, \
    MainDirectoryTree, MainFileSelector, get_gtk_bookmarks, parse_gtk_bookmarks
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

        data = (b"file:///foo/bar\nfile:///home/user\n"
                b"file:///home/user/Downloads Downloads\n")
        paths = parse_gtk_bookmarks(data)
        assert all(isinstance(p, fsnative) for p in paths)


class TDirectoryTree(TestCase):

    if os.name == "nt":
        ROOTS = [get_home_dir(), u"C:\\"]
    else:
        ROOTS = [get_home_dir(), "/"]

    def setUp(self):
        quodlibet.config.init()

    def tearDown(self):
        quodlibet.config.quit()

    def test_initial(self):
        if os.name == "nt":
            paths = [u"C:\\", get_home_dir()]
        else:
            paths = ["/", get_home_dir()]

        for path in paths:
            dirlist = DirectoryTree(path, folders=self.ROOTS)
            model, rows = dirlist.get_selection().get_selected_rows()
            selected = [model[row][0] for row in rows]
            dirlist.destroy()
            self.failUnlessEqual([os.path.normpath(path)], selected)

    def test_bad_initial(self):
        invalid = os.path.join("bin", "file", "does", "not", "exist")
        for path in self.ROOTS:
            newpath = os.path.join(path, invalid)
            dirlist = DirectoryTree(newpath, folders=self.ROOTS)
            selected = dirlist.get_selected_paths()
            dirlist.destroy()
            # select the last valid parent directory
            self.assertEqual(len(selected), 1)
            self.assertTrue(selected[0].startswith(path))

    def test_bad_go_to(self):
        newpath = fsnative(u"/woooooo/bar/fun/broken")
        dirlist = DirectoryTree(fsnative(u"/"), folders=self.ROOTS)
        dirlist.go_to(newpath)
        dirlist.destroy()

    def test_main(self):
        folders = ["/"]
        if os.name == "nt":
            folders = [u"C:\\"]
        main = MainDirectoryTree(folders=folders)
        self.assertTrue(len(main.get_model()))

        main = MainDirectoryTree()
        self.assertTrue(len(main.get_model()))

    def test_get_drives(self):
        for path in get_drives():
            self.assertTrue(isinstance(path, fsnative))

    def test_popup(self):
        dt = DirectoryTree(None, folders=self.ROOTS)
        menu = dt._create_menu()
        dt._popup_menu(menu)
        children = menu.get_children()
        self.failUnlessEqual(len(children), 4)
        delete = children[1]
        self.failUnlessEqual(delete.get_label(), __("_Delete"))
        self.failUnless(delete.get_sensitive())

    def test_multiple_selections(self):
        dt = DirectoryTree(None, folders=self.ROOTS)
        menu = dt._create_menu()
        dt._popup_menu(menu)
        children = menu.get_children()
        select_sub = children[3]
        self.failUnless("sub-folders" in select_sub.get_label().lower())
        self.failUnless(select_sub.get_sensitive())
        sel = dt.get_selection()
        model = dt.get_model()
        for it, _pth in model.iterrows(None):
            sel.select_iter(it)
        self.failUnless(select_sub.get_sensitive(),
                        msg="Select All should work for multiple")
        self.failIf(children[0].get_sensitive(),
                    msg="New Folder should be disabled for multiple")
        self.failUnless(children[3].get_sensitive(),
                        msg="Refresh should be enabled for multiple")


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
            initial=self.INITIAL, filter=(lambda s: s in self.PATHS),
            folders=self.ROOTS)
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
