# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from tests import TestCase, mkdtemp
from tests.helper import __

import os
import shutil
import sys
from unittest import mock

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

    def test_hidden_navigation(self):
        root = mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        visible = os.path.join(root, "visible")
        store = os.path.join(visible, ".store")
        target = os.path.join(store, "album", ".disc")
        os.makedirs(target)
        os.mkdir(os.path.join(visible, ".unrelated"))

        for initial in (target, visible):
            tree = DirectoryTree(initial, folders=[root])
            self.addCleanup(tree.destroy)
            model = tree.get_model()
            self.assertEqual(tree.get_selected_paths(), [initial])
            if initial == visible:
                tree.expand_row(model.get_path(model.get_iter_first()), False)
                parent = model.iter_children(model.get_iter_first())
                self.assertFalse(model.iter_has_child(parent))
            tree.go_to(target)
            self.assertEqual(tree.get_selected_paths(), [target])
            tree.go_to(target)
            tree.collapse_all()
            tree.go_to(target)
            self.assertEqual(tree.get_selected_paths(), [target])

            tree.go_to(visible)
            menu = tree._create_menu()
            self.addCleanup(menu.destroy)
            menu.get_children()[2].activate()
            tree.go_to(target)
            self.assertEqual(tree.get_selected_paths(), [target])
            parent = model.iter_children(model.get_iter_first())
            self.assertEqual([p for _, p in model.iterrows(parent)], [store])

            # Reveal another child of an already expanded directory.
            tree.go_to(os.path.join(visible, ".unrelated"))
            tree.go_to(os.path.join(visible, ".unrelated"))
            self.assertEqual(
                tree.get_selected_paths(), [os.path.join(visible, ".unrelated")]
            )
            self.assertEqual(
                [p for _, p in model.iterrows(parent)],
                [store, os.path.join(visible, ".unrelated")],
            )

    def test_hidden_navigation_fallback(self):
        root = mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        hidden = os.path.join(root, ".store")
        os.mkdir(hidden)
        file_ = os.path.join(hidden, "file")
        open(file_, "wb").close()
        tree = DirectoryTree(root, folders=[root])
        self.addCleanup(tree.destroy)
        for target, expected in (
            (os.path.join(root, ".missing", "album"), root),
            (os.path.join(file_, "album"), hidden),
            (os.path.join(hidden, "missing"), hidden),
        ):
            tree.go_to(target)
            self.assertEqual(tree.get_selected_paths(), [expected])
        tree.collapse_all()
        with mock.patch("os.listdir", side_effect=OSError):
            tree.go_to(hidden)
        self.assertEqual(tree.get_selected_paths(), [root])

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
        children = menu.get_children()
        self.assertEqual(len(children), 4)
        delete = children[1]
        self.assertEqual(delete.get_label(), __("_Delete"))
        assert delete.get_sensitive()

    def test_multiple_selections(self):
        dt = DirectoryTree(None, folders=self.ROOTS)
        menu = dt._create_menu()
        dt._popup_menu(menu)
        children = menu.get_children()
        select_sub = children[3]
        assert "sub-folders" in select_sub.get_label().lower()
        assert select_sub.get_sensitive()
        sel = dt.get_selection()
        model = dt.get_model()
        for it, _pth in model.iterrows(None):
            sel.select_iter(it)
        assert select_sub.get_sensitive(), "Select All should work for multiple"
        msg = "New Folder should be disabled for multiple"
        assert not children[0].get_sensitive(), msg
        assert children[3].get_sensitive(), "Refresh should be enabled for multiple"


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

    def test_hidden_directory(self):
        root = os.path.realpath(mkdtemp())
        self.addCleanup(shutil.rmtree, root)
        target = os.path.join(root, ".store", "album")
        os.makedirs(target)
        file_ = os.path.join(target, "song")
        open(file_, "wb").close()
        for initial in (target, root):
            selector = FileSelector(
                initial=initial, filter=lambda p: p == file_, folders=[root]
            )
            self.addCleanup(selector.destroy)
            if initial == root:
                selector.go_to(target)
            filelist = selector.get_child2().get_child()
            self.assertEqual([p for _, p in filelist.get_model().iterrows()], [file_])

        link = os.path.join(root, "link")
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError):
            return
        selector = FileSelector(
            initial=os.path.realpath(link),
            filter=lambda p: p == file_,
            folders=[root],
        )
        self.addCleanup(selector.destroy)
        filelist = selector.get_child2().get_child()
        self.assertEqual([p for _, p in filelist.get_model().iterrows()], [file_])

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
