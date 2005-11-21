# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import shutil
import dircache

import gobject, gtk

import formats
import qltk
import util

def search_func(model, column, key, iter, handledirs):
    check = model.get_value(iter, 0)
    if not handledirs or '/' not in key:
        check = os.path.basename(check) or '/'
    return key not in check.lower() and key not in check

class DirectoryTree(gtk.TreeView):
    def cell_data(column, cell, model, iter):
        cell.set_property('text', util.fsdecode(
            os.path.basename(model[iter][0])) or "/")
    cell_data = staticmethod(cell_data)

    def __init__(self, initial=None):
        gtk.TreeView.__init__(self, gtk.TreeStore(str))
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
        # FIXME: Fuck you fuck you fuck you fuck you GTK.
        #self.set_search_equal_func(search_func, True)
        folders = [os.environ["HOME"], "/"]
        # Read in the GTK bookmarks list; gjc says this is the right way
        try: f = file(os.path.join(os.environ["HOME"], ".gtk-bookmarks"))
        except EnvironmentError: pass
        else:
            import urlparse
            for line in f.readlines():
                folders.append(urlparse.urlsplit(line.rstrip())[2])
            folders = filter(os.path.isdir, folders)

        for path in folders:
            niter = self.get_model().append(None, [path])
            self.get_model().append(niter, ["dummy"])
        self.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.connect(
            'test-expand-row', DirectoryTree.__expanded, self.get_model())

        if initial: self.go_to(initial)

        menu = gtk.Menu()
        m = qltk.MenuItem(_("New Folder..."), gtk.STOCK_NEW)
        m.connect('activate', self.__mkdir)
        menu.append(m)
        m = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        m.connect('activate', self.__rmdir)
        menu.append(m)
        m = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        m.connect('activate', self.__refresh)
        menu.append(m)
        menu.show_all()
        self.connect('button-press-event', DirectoryTree.__button_press, menu)

    def go_to(self, initial):
        path = []
        head, tail = os.path.split(initial)
        while head != os.path.dirname(os.environ["HOME"]) and tail != '':
            if tail:
                def isvisibledir(t):
                    return t[0] != "." and os.path.isdir(os.path.join(head, t))
                try: dirs = filter(isvisibledir, dircache.listdir(head))
                except OSError: break
                try: path.insert(0, dirs.index(tail))
                except ValueError: break
            head, tail = os.path.split(head)

        if initial.startswith(os.environ["HOME"]): path.insert(0, 0)
        else: path.insert(0, 1)
        for i in range(len(path)):
            self.expand_row(tuple(path[:i+1]), False)
        self.get_selection().select_path(tuple(path))
        self.scroll_to_cell(tuple(path))

    def __button_press(self, event, menu):
        if event.button != 3: return False
        x, y = map(int, [event.x, event.y])
        model = self.get_model()
        try: path, col, cellx, celly = self.get_path_at_pos(x, y)
        except TypeError: return True
        directory = model[path][0]
        delete = menu.get_children()[1]
        try: delete.set_sensitive(len(os.listdir(directory)) == 0)
        except OSError, err:
            if err.errno == 2: model.remove(model.get_iter(path))
        else:
            selection = self.get_selection()
            selection.unselect_all()
            selection.select_path(path)
            menu.popup(None, None, None, event.button, event.time)
            return True

    def __mkdir(self, button):
        model, rows = self.get_selection().get_selected_rows()
        if len(rows) != 1: return

        row = rows[0]
        directory = model[row][0]
        dir = qltk.GetStringDialog(
            None, _("New Folder"), _("Enter a name for the new folder:")).run()

        if dir:
            dir = util.fsencode(dir.decode('utf-8'))
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
            while gtk.events_pending(): gtk.main_iteration()
        try:
            if model is None: return
            while model.iter_has_child(iter):
                model.remove(model.iter_children(iter))
            folder = model[iter][0]
            for base in dircache.listdir(folder):
                path = os.path.join(folder, base)
                if (base[0] != "." and os.access(path, os.R_OK) and
                    os.path.isdir(path)):
                    niter = model.append(iter, [path])
                    if filter(os.path.isdir,
                              [os.path.join(path, d) for d in
                               dircache.listdir(path) if d[0] != "."]):
                        model.append(niter, ["dummy"])
            if not model.iter_has_child(iter): return True
        finally:
            if window: window.set_cursor(None)

class FileSelector(gtk.VPaned):
    def cell_data(column, cell, model, iter):
        cell.set_property(
            'text', util.fsdecode(os.path.basename(model[iter][0])))
    cell_data = staticmethod(cell_data)

    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (gtk.TreeSelection,))
                     }

    def __init__(self, initial=None, filter=formats.filter):
        gtk.VPaned.__init__(self)
        self.__filter = filter

        dirlist = DirectoryTree(initial)
        filelist = qltk.HintedTreeView(gtk.ListStore(str))
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
        #filelist.set_search_equal_func(search_func, False)

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

    def rescan(self):
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
            for file in filter(self.__filter, dircache.listdir(dir)):
                fmodel.append([os.path.join(dir, file)])
        def select_paths(model, path, iter, selection):
            if model[path][0] in selected:
                selection.select_path(path)
        if fmodel: fmodel.foreach(select_paths, fselect)
        fselect.handler_unblock(self.__sig)
        fselect.emit('changed')

gobject.type_register(FileSelector)
