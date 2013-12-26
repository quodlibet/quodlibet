# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import urlparse
import errno

from gi.repository import Gtk, GObject, Gdk

from quodlibet import const
from quodlibet import formats
from quodlibet import qltk
from quodlibet import util
from quodlibet import windows

from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.views import AllTreeView, RCMTreeView, MultiDragTreeView
from quodlibet.qltk.views import TreeViewColumn
from quodlibet.qltk.x import ScrolledWindow
from quodlibet.qltk.models import ObjectStore, ObjectTreeStore

from quodlibet.util.path import fsdecode, listdir


def search_func(model, column, key, iter_, handledirs):
    check = model.get_value(iter_, 0)
    if check is None:
        return True
    elif not handledirs or os.sep not in key:
        check = os.path.basename(check) or os.sep
    return key not in check.lower() and key not in check


def filesel_filter(filename):
    IMAGES = [".jpg", ".png", ".jpeg"]
    if formats.filter(filename):
        return True
    else:
        for ext in IMAGES:
            if filename.lower().endswith(ext):
                return True
    return False


def _get_win_favorites():
    """Returns a list of paths for commonly used directories.

    e.g. My Music, Desktop etc.
    """

    assert os.name == "nt"

    folders = []

    funcs = [windows.get_desktop_dir, windows.get_personal_dir,
             windows.get_music_dir]

    for func in funcs:
        path = func()
        if path is not None:
            folders.append(path)

    return folders


def get_favorites():
    """A list of paths of commonly used folders (Desktop,..)

    Paths don't have to exist.
    """

    if os.name == "nt":
        return _get_win_favorites()
    else:
        return [const.HOME, "/"]


def _get_win_drives():
    """Returns a list of paths for all available drives e.g. ['C:\\']"""

    assert os.name == "nt"
    drives = [letter + ":\\" for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ"]
    return [d for d in drives if os.path.isdir(d)]


def get_drives():
    """A list of accessible drives"""

    if os.name == "nt":
        return _get_win_drives()
    else:
        return []


def get_gtk_bookmarks():
    """A list of paths from the GTK+ bookmarks.

    The paths don't have to exist.
    """

    path = os.path.join(const.HOME, ".gtk-bookmarks")
    folders = []
    try:
        with open(path, "rb") as f:
            for line in f.readlines():
                parts = line.split()
                if not parts:
                    continue
                folder_url = parts[0]
                folders.append(urlparse.urlsplit(folder_url)[2])
    except EnvironmentError:
        pass

    return folders


class DirectoryTree(RCMTreeView, MultiDragTreeView):
    """A tree view showing multiple folder hierarchies"""

    def __init__(self, initial=None, folders=None):
        """
        initial -- the path to select/scroll to
        folders -- a list of paths to show in the tree view, None
                   will result in a separator.
        """

        model = ObjectTreeStore()
        super(DirectoryTree, self).__init__(model)

        if initial is not None:
            initial = util.fsnative(initial)

        column = TreeViewColumn(_("Folders"))
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        render = Gtk.CellRendererPixbuf()
        render.set_property('stock_id', Gtk.STOCK_DIRECTORY)
        column.pack_start(render, False)
        render = Gtk.CellRendererText()
        column.pack_start(render, True)

        def cell_data(column, cell, model, iter_, userdata):
            value = model.get_value(iter_)
            if value is not None:
                text = fsdecode(os.path.basename(value) or value)
                cell.set_property('text', text)

        column.set_cell_data_func(render, cell_data)

        self.append_column(column)
        self.set_search_equal_func(search_func, True)

        if folders is None:
            folders = []

        for path in folders:
            niter = model.append(None, [path])
            if path is not None:
                model.append(niter, ["dummy"])

        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.connect(
            'test-expand-row', DirectoryTree.__expanded, model)

        self.set_row_separator_func(
            lambda model, iter_, data: model.get_value(iter_) is None, None)

        if initial:
            self.go_to(initial)

        menu = Gtk.Menu()
        m = qltk.MenuItem(_("_New Folder..."), Gtk.STOCK_NEW)
        m.connect('activate', self.__mkdir)
        menu.append(m)
        m = Gtk.ImageMenuItem(Gtk.STOCK_DELETE, use_stock=True)
        m.connect('activate', self.__rmdir)
        menu.append(m)
        m = Gtk.ImageMenuItem(Gtk.STOCK_REFRESH, use_stock=True)
        m.connect('activate', self.__refresh)
        menu.append(m)
        m = qltk.MenuItem(_("_Select All Subfolders"), Gtk.STOCK_DIRECTORY)
        m.connect('activate', self.__expand)
        menu.append(m)
        menu.show_all()
        self.connect_object('popup-menu', self.__popup_menu, menu)

    def get_selected_paths(self):
        """A list of fs paths"""

        selection = self.get_selection()
        model, paths = selection.get_selected_rows()
        return [model[p][0] for p in paths]

    def go_to(self, path_to_go):
        # FIXME: this works on the FS instead of the model
        # and expects fixed initial folders

        path_to_go = util.fsnative(path_to_go)

        path = []
        head, tail = os.path.split(path_to_go)
        while os.path.join(head, tail) != const.HOME and tail != '':
            if tail:
                def isvisibledir(t):
                    joined = os.path.join(head, t)
                    return (not t.startswith(".") and
                            os.access(joined, os.X_OK) and
                            os.path.isdir(joined))
                try:
                    dirs = filter(isvisibledir, sorted(os.listdir(head)))
                except OSError:
                    break
                try:
                    path.insert(0, dirs.index(tail))
                except ValueError:
                    break
            head, tail = os.path.split(head)

        if path_to_go.startswith(const.HOME):
            path.insert(0, 0)
        else:
            path.insert(0, 1)

        for i in range(len(path)):
            self.expand_row(Gtk.TreePath(tuple(path[:i + 1])), False)

        tree_path = Gtk.TreePath(tuple(path))
        self.get_selection().select_path(tree_path)
        try:
            self.get_model().get_iter(tree_path)
        except ValueError:
            pass
        else:
            self.scroll_to_cell(tree_path)

    def __popup_menu(self, menu):
        model, paths = self.get_selection().get_selected_rows()
        if len(paths) != 1:
            return True

        path = paths[0]
        directory = model[path][0]
        delete = menu.get_children()[1]
        try:
            delete.set_sensitive(len(os.listdir(directory)) == 0)
        except OSError, err:
            if err.errno == errno.ENOENT:
                model.remove(model.get_iter(path))
            return False

        selection = self.get_selection()
        selection.unselect_all()
        selection.select_path(path)
        return self.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __mkdir(self, button):
        model, paths = self.get_selection().get_selected_rows()
        if len(paths) != 1:
            return

        path = paths[0]
        directory = model[path][0]

        dir_ = GetStringDialog(
            None, _("New Folder"), _("Enter a name for the new folder:")).run()

        if not dir_:
            return

        dir_ = util.fsnative(dir_.decode('utf-8'))
        fullpath = os.path.realpath(os.path.join(directory, dir_))

        try:
            os.makedirs(fullpath)
        except EnvironmentError, err:
            error = "<b>%s</b>: %s" % (err.filename, err.strerror)
            qltk.ErrorMessage(
                None, _("Unable to create folder"), error).run()
            return

        self.emit('test-expand-row', model.get_iter(path), path)
        self.expand_row(path, False)

    def __rmdir(self, button):
        model, paths = self.get_selection().get_selected_rows()
        if len(paths) != 1:
            return

        directory = model[paths[0]][0]
        try:
            os.rmdir(directory)
        except EnvironmentError, err:
            error = "<b>%s</b>: %s" % (err.filename, err.strerror)
            qltk.ErrorMessage(
                None, _("Unable to delete folder"), error).run()
            return

        ppath = Gtk.TreePath(paths[0][:-1])
        expanded = self.row_expanded(ppath)
        self.emit('test-expand-row', model.get_iter(ppath), ppath)
        if expanded:
            self.expand_row(ppath, False)

    def __expand(self, button):
        selection = self.get_selection()
        model, paths = selection.get_selected_rows()

        for path in paths:
            iter_ = model.get_iter(path)
            self.expand_row(path, False)
            last = self.__select_children(iter_, model, selection)
            selection.select_range(path, last)

    def __select_children(self, iter_, model, selection):
        nchildren = model.iter_n_children(iter_)
        last = model.get_path(iter_)

        for i in xrange(nchildren):
            child = model.iter_nth_child(iter_, i)
            self.expand_row(model.get_path(child), False)
            last = self.__select_children(child, model, selection)
        return last

    def __refresh(self, button):
        model, rows = self.get_selection().get_selected_rows()
        expanded = set()
        self.map_expanded_rows(
            lambda s, iter, data: expanded.add(model[iter][0]), None)
        needs_expanding = []
        for row in rows:
            if self.row_expanded(row):
                self.emit('test-expand-row', model.get_iter(row), row)
                self.expand_row(row, False)
                needs_expanding.append(row)
        while len(needs_expanding) > 0:
            child = model.iter_children(model.get_iter(needs_expanding.pop()))
            while child is not None:
                if model[child][0] in expanded:
                    path = model.get_path(child)
                    self.emit('test-expand-row', child, path)
                    self.expand_row(path, False)
                    needs_expanding.append(path)
                child = model.iter_next(child)

    def __expanded(self, iter, path, model):
        window = self.get_window()
        if window:
            window.set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
            Gtk.main_iteration_do(False)
        try:
            try:
                if model is None:
                    return
                while model.iter_has_child(iter):
                    model.remove(model.iter_children(iter))
                folder = model[iter][0]
                for path in listdir(folder):
                    try:
                        if not os.path.isdir(path):
                            continue
                        for filename in listdir(path):
                            if os.path.isdir(filename):
                                niter = model.append(iter, [path])
                                model.append(niter, ["dummy"])
                                break
                        else:
                            model.append(iter, [path])
                    except OSError:
                        pass
                if not model.iter_has_child(iter):
                    return True
            except OSError:
                pass
        finally:
            if window:
                window.set_cursor(None)


class FileSelector(Gtk.VPaned):
    """A file selector widget consisting of a folder tree
    and a file list below.
    """

    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_LAST, None,
                    (Gtk.TreeSelection,))
    }

    def __init__(self, initial=None, filter=filesel_filter, folders=None):
        """
        initial -- a path to a file which should be shown initially
        filter -- a function which filters paths shown in the file list
        folders -- list of shown folders in the directory tree
        """

        super(FileSelector, self).__init__()
        self.__filter = filter

        if initial is not None:
            initial = util.fsnative(initial)

        if initial and os.path.isfile(initial):
            initial = os.path.dirname(initial)
        dirlist = DirectoryTree(initial, folders=folders)

        model = ObjectStore()
        filelist = AllTreeView(model)

        column = TreeViewColumn(_("Songs"))
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        render = Gtk.CellRendererPixbuf()
        render.set_property('stock_id', Gtk.STOCK_FILE)
        render.props.xpad = 3
        column.pack_start(render, False)
        render = Gtk.CellRendererText()
        column.pack_start(render, True)

        def cell_data(column, cell, model, iter_, userdata):
            value = model.get_value(iter_)
            cell.set_property('text', fsdecode(os.path.basename(value)))

        column.set_cell_data_func(render, cell_data)

        filelist.append_column(column)
        filelist.set_rules_hint(True)
        filelist.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        filelist.set_search_equal_func(search_func, False)

        self.__sig = filelist.get_selection().connect(
            'changed', self.__changed)

        dirlist.get_selection().connect(
            'changed', self.__dir_selection_changed, filelist)
        dirlist.get_selection().emit('changed')

        def select_all_files(view, path, col, fileselection):
            view.expand_row(path, False)
            fileselection.select_all()
        dirlist.connect('row-activated', select_all_files,
            filelist.get_selection())

        sw = ScrolledWindow()
        sw.add(dirlist)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.pack1(sw, resize=True)

        sw = ScrolledWindow()
        sw.add(filelist)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        self.pack2(sw, resize=True)

    def get_selected_paths(self):
        """A list of fs paths"""

        filelist = self.get_child2().get_child()
        selection = filelist.get_selection()
        model, paths = selection.get_selected_rows()
        return [model[p][0] for p in paths]

    def rescan(self):
        """Refill the file list for the current directory selection"""

        dirlist = self.get_child1().get_child()
        filelist = self.get_child2().get_child()

        dir_selection = dirlist.get_selection()
        self.__dir_selection_changed(dir_selection, filelist)

    def __changed(self, selection):
        # forward file list selection changed signals
        self.emit('changed', selection)

    def __dir_selection_changed(self, selection, filelist):
        # dir selection changed, refill the file list

        fselect = filelist.get_selection()
        fselect.handler_block(self.__sig)
        fmodel, frows = fselect.get_selected_rows()
        selected = [fmodel[row][0] for row in frows]

        fmodel = filelist.get_model()
        fmodel.clear()
        dmodel, rows = selection.get_selected_rows()
        dirs = [dmodel[row][0] for row in rows]
        for dir_ in dirs:
            try:
                files = filter(self.__filter, listdir(dir_))
                for file_ in sorted(files):
                    filename = os.path.join(dir_, file_)
                    if (os.access(filename, os.R_OK) and
                            not os.path.isdir(filename)):
                        fmodel.append([filename])
            except OSError:
                pass

        for iter_, filename in fmodel.iterrows():
            if filename in selected:
                fselect.select_iter(iter_)

        fselect.handler_unblock(self.__sig)
        fselect.emit('changed')


def _get_main_folders():

    def filter_exists(paths):
        return [p for p in paths if os.path.isdir(p)]

    folders = []

    favs = filter_exists(get_favorites())
    if favs:
        folders += favs

    drives = filter_exists(get_drives())
    if folders and drives:
        folders += [None]
    if drives:
        folders += drives

    bookmarks = filter_exists(get_gtk_bookmarks())
    if folders and bookmarks:
        folders += [None]
    if bookmarks:
        folders += bookmarks

    return folders


class MainFileSelector(FileSelector):
    """The main file selector used in EF.

    Shows a useful list of directories in the directory tree.
    """

    def __init__(self, initial=None):
        folders = _get_main_folders()
        super(MainFileSelector, self).__init__(
            initial, self._filesel_filter, folders=folders)

    @staticmethod
    def _filesel_filter(filename):
        IMAGES = [".jpg", ".png", ".jpeg"]
        if formats.filter(filename):
            return True
        else:
            for ext in IMAGES:
                if filename.lower().endswith(ext):
                    return True
        return False


class MainDirectoryTree(DirectoryTree):
    """The main directory tree used in QL.

    Shows a useful list of directories.
    """

    def __init__(self, initial=None, folders=None):
        if folders is None:
            folders = []

        main = _get_main_folders()
        if folders and main:
            folders += [None]
        if main:
            folders += main

        super(MainDirectoryTree, self).__init__(
            initial=initial, folders=folders)
