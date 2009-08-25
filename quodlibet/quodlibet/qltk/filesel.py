# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import urlparse

import gobject
import gtk

from quodlibet import const
from quodlibet import formats
from quodlibet import qltk
from quodlibet import util

from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.views import AllTreeView, RCMTreeView, MultiDragTreeView

def search_func(model, column, key, iter, handledirs):
    check = model.get_value(iter, 0)
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

class DirectoryTree(RCMTreeView, MultiDragTreeView):
    def cell_data(column, cell, model, iter):
        value = model[iter][0]
        if value is not None:
            cell.set_property('text', util.fsdecode(
                os.path.basename(value) or value))
    cell_data = staticmethod(cell_data)

    def __init__(self, initial=None, folders=[const.HOME, "/"]):
        super(DirectoryTree, self).__init__(gtk.TreeStore(str))
        column = gtk.TreeViewColumn(_("Folders"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        render = gtk.CellRendererPixbuf()
        render.set_property('stock_id', gtk.STOCK_DIRECTORY)
        column.pack_start(render, expand=False)
        render = gtk.CellRendererText()
        column.pack_start(render)
        column.set_cell_data_func(render, self.cell_data)

        column.set_attributes(render, text=0)
        self.append_column(column)
        self.set_search_equal_func(search_func, True)

        # Read in the GTK bookmarks list; gjc says this is the right way
        try: f = file(os.path.join(const.HOME, ".gtk-bookmarks"))
        except EnvironmentError: pass
        else:
            folders.append(None)
            for line in f.readlines():
                folders.append(urlparse.urlsplit(line.rstrip())[2])

        def is_folder(filename):
            return filename is None or os.path.isdir(filename)
        folders = filter(is_folder, folders)
        if folders[-1] is None:
            folders.pop()

        for path in folders:
            niter = self.get_model().append(None, [path])
            if path is not None:
                self.get_model().append(niter, ["dummy"])
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.connect(
            'test-expand-row', DirectoryTree.__expanded, self.get_model())
        self.set_row_separator_func(lambda model, iter: model[iter][0] is None)

        if initial: self.go_to(initial)

        menu = gtk.Menu()
        m = qltk.MenuItem(_("_New Folder..."), gtk.STOCK_NEW)
        m.connect('activate', self.__mkdir)
        menu.append(m)
        m = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        m.connect('activate', self.__rmdir)
        menu.append(m)
        m = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        m.connect('activate', self.__refresh)
        menu.append(m)
        m = qltk.MenuItem(_("_Select All Subfolders"), gtk.STOCK_DIRECTORY)
        m.connect('activate', self.__expand)
        menu.append(m)
        menu.show_all()
        self.connect_object('popup-menu', self.__popup_menu, menu)

    def go_to(self, initial):
        path = []
        head, tail = os.path.split(initial)
        while os.path.join(head, tail) != const.HOME and tail != '':
            if tail:
                def isvisibledir(t):
                    joined = os.path.join(head, t)
                    return (not t.startswith(".") and
                            os.access(joined, os.X_OK) and
                            os.path.isdir(joined))
                try: dirs = filter(isvisibledir,
                                   sorted(os.listdir(util.fsnative(head))))
                except OSError: break
                try: path.insert(0, dirs.index(tail))
                except ValueError: break
            head, tail = os.path.split(head)

        if initial.startswith(const.HOME):
            path.insert(0, 0)
        else: path.insert(0, 1)
        for i in range(len(path)):
            self.expand_row(tuple(path[:i+1]), False)
        self.get_selection().select_path(tuple(path))
        self.scroll_to_cell(tuple(path))

    def __popup_menu(self, menu):
        try: model, (path,) = self.get_selection().get_selected_rows()
        except ValueError: return True
        directory = model[path][0]
        delete = menu.get_children()[1]
        try: delete.set_sensitive(len(os.listdir(util.fsnative(directory))) == 0)
        except OSError, err:
            if err.errno == 2: model.remove(model.get_iter(path))
        else:
            selection = self.get_selection()
            selection.unselect_all()
            selection.select_path(path)
            return self.popup_menu(menu, 0, gtk.get_current_event_time())

    def __mkdir(self, button):
        model, rows = self.get_selection().get_selected_rows()
        if len(rows) != 1: return

        row = rows[0]
        directory = model[row][0]
        dir = GetStringDialog(
            None, _("New Folder"), _("Enter a name for the new folder:")).run()

        if dir:
            dir = util.fsnative(dir.decode('utf-8'))
            fullpath = os.path.realpath(os.path.join(directory, dir))
            try: os.makedirs(fullpath)
            except EnvironmentError, err:
                error = "<b>%s</b>: %s" % (err.filename, err.strerror)
                qltk.ErrorMessage(
                    None, _("Unable to create folder"), error).run()
            else:
                self.emit('test-expand-row', model.get_iter(row), row)
                self.expand_row(row, False)

    def __rmdir(self, button):
        model, rows = self.get_selection().get_selected_rows()
        if len(rows) != 1: return
        directory = model[rows[0]][0]
        try: os.rmdir(directory)
        except EnvironmentError, err:
            error = "<b>%s</b>: %s" % (err.filename, err.strerror)
            qltk.ErrorMessage(
                None, _("Unable to delete folder"), error).run()
        else:
            prow = rows[0][:-1]
            expanded = self.row_expanded(prow)
            self.emit('test-expand-row', model.get_iter(prow), prow)
            if expanded: self.expand_row(prow, False)

    def __expand(self, button):
        selection = self.get_selection()
        model, rows = selection.get_selected_rows()
        for row in rows:
            it = model.get_iter(row)
            self.expand_row(row, False)
            last = self.__select_children(it, model, selection)
            selection.select_range(row, last)

    def __select_children(self, iter, model, selection):
        nchildren = model.iter_n_children(iter)
        last = model.get_path(iter)
        for i in xrange(nchildren):
            child = model.iter_nth_child(iter, i)
            self.expand_row(model.get_path(child), False)
            last = self.__select_children(child, model, selection)
        return last

    def __refresh(self, button):
        model, rows = self.get_selection().get_selected_rows()
        for row in rows:
            if self.row_expanded(row):
                self.emit('test-expand-row', model.get_iter(row), row)
                self.expand_row(row, False)

    def __expanded(self, iter, path, model):
        window = self.window
        if window:
            window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
            gtk.main_iteration()
        try:
            try:
                if model is None:
                    return
                while model.iter_has_child(iter):
                    model.remove(model.iter_children(iter))
                folder = model[iter][0]
                for path in util.listdir(folder):
                    try:
                        for filename in util.listdir(path):
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

class FileSelector(gtk.VPaned):
    def cell_data(column, cell, model, iter):
        value = model[iter][0]
        if value is not None:
            cell.set_property('text', util.fsdecode(os.path.basename(value)))
    cell_data = staticmethod(cell_data)

    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (gtk.TreeSelection,))
                     }

    def __init__(self, initial=None, filter=filesel_filter,
                 folders=[const.HOME, "/"]):
        super(FileSelector, self).__init__()
        self.__filter = filter

        dirlist = DirectoryTree(initial, folders=folders)
        filelist = AllTreeView(gtk.ListStore(str))
        column = gtk.TreeViewColumn(_("Songs"))
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        render = gtk.CellRendererPixbuf()
        render.set_property('stock_id', gtk.STOCK_FILE)
        column.pack_start(render, expand=False)
        render = gtk.CellRendererText()
        column.pack_start(render)
        column.set_cell_data_func(render, self.cell_data)
        column.set_attributes(render, text=0)
        filelist.append_column(column)
        filelist.set_rules_hint(True)
        filelist.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        filelist.set_search_equal_func(search_func, False)

        self.__sig = filelist.get_selection().connect(
            'changed', self.__changed)

        dirlist.get_selection().connect(
            'changed', self.__fill, filelist)
        dirlist.get_selection().emit('changed')
        def select_all_files(view, path, col, fileselection):
            view.expand_row(path, False)
            fileselection.select_all()
        dirlist.connect('row-activated', select_all_files,
            filelist.get_selection())

        sw = gtk.ScrolledWindow()
        sw.add(dirlist)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.pack1(sw, resize=True)

        sw = gtk.ScrolledWindow()
        sw.add(filelist)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.set_shadow_type(gtk.SHADOW_IN)
        self.pack2(sw, resize=True)

    def rescan(self, *args):
        self.get_child1().child.get_selection().emit('changed')

    def __changed(self, selection):
        self.emit('changed', selection)

    def __fill(self, selection, filelist):
        fselect = filelist.get_selection()
        fselect.handler_block(self.__sig)
        fmodel, frows = fselect.get_selected_rows()
        selected = [fmodel[row][0] for row in frows]
        fmodel = filelist.get_model()
        fmodel.clear()
        dmodel, rows = selection.get_selected_rows()
        dirs = [dmodel[row][0] for row in rows]
        for dir in dirs:
            try:
                for file in filter(self.__filter,
                                   sorted(os.listdir(util.fsencode(dir)))):
                    filename = os.path.join(dir, file)
                    if os.access(filename, os.R_OK):
                        fmodel.append([filename])
            except OSError:
                pass

        for row in fmodel:
            if row[0] in selected:
                fselect.select_path(row.path)
        fselect.handler_unblock(self.__sig)
        fselect.emit('changed')
