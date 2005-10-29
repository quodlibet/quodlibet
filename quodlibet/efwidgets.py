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
import gtk, gobject

import const
import formats
import qltk
import util

from properties import SongProperties
from plugins import PluginManager

class EFPluginManager(PluginManager):
    # Ex Falso doesn't send events; it also should enable all
    # invokable plugins since there's no configuration.
    def rescan(self):
        super(EFPluginManager, self).rescan()
        for plugin in self.plugins.values(): self.enable(plugin, True)
        return []

    def invoke_event(self, event, *args): pass

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
        if window: window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))
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

class ExFalsoWindow(gtk.Window):
    __gsignals__ = { 'changed': (gobject.SIGNAL_RUN_LAST,
                                 gobject.TYPE_NONE, (object,))
                     }

    def __init__(self, watcher, dir=None):
        gtk.Window.__init__(self)
        self.set_title("Ex Falso")
        icon_theme = gtk.icon_theme_get_default()
        p = gtk.gdk.pixbuf_new_from_file("exfalso.png")
        gtk.icon_theme_add_builtin_icon(const.ICON, 64, p)
        self.set_icon(icon_theme.load_icon(
            const.ICON, 64, gtk.ICON_LOOKUP_USE_BUILTIN))
        self.set_border_width(12)
        self.set_default_size(700, 500)
        self.add(gtk.HPaned())
        fs = FileSelector(dir)
        self.child.pack1(fs, resize=True)
        nb = qltk.Notebook()
        nb.append_page(SongProperties.Information(self, library=False))
        for Page in [SongProperties.EditTags,
                     SongProperties.TagByFilename,
                     SongProperties.RenameFiles,
                     SongProperties.TrackNumbers]:
            nb.append_page(Page(self, watcher))
        self.child.pack2(nb, resize=False, shrink=False)
        fs.connect('changed', self.__changed, nb)
        self.__cache = {}
        s = watcher.connect_object('refresh', FileSelector.rescan, fs)
        self.connect_object('destroy', watcher.disconnect, s)
        self.__save = None
        self.connect_object('changed', self.set_pending, None)
        for c in fs.get_children():
            c.child.connect('button-press-event', self.__pre_selection_changed)
        fs.get_children()[1].child.connect(
            'button-press-event', self.__button_press, fs)
        fs.get_children()[1].child.connect(
            'popup-menu', self.__popup_menu, fs)
        self.emit('changed', [])

        # plugin support
        self.pm = EFPluginManager(watcher, ["./plugins", const.PLUGINS])
        self.pm.rescan()

    def set_pending(self, button, *excess):
        self.__save = button

    def __pre_selection_changed(self, view, event):
        if self.__save:
            resp = qltk.CancelRevertSave(self).run()
            if resp == gtk.RESPONSE_YES: self.__save.clicked()
            elif resp == gtk.RESPONSE_NO: return False
            else: return True # cancel or closed

    def __button_press(self, view, event, fs):
        if event.button == 3:
            x, y = map(int, [event.x, event.y])
            try: path, col, cellx, celly = view.get_path_at_pos(x, y)
            except TypeError: return True
            selection = view.get_selection()
            if not selection.path_is_selected(path):
                view.set_cursor(path, col, 0)
            return self.__show_menu(view, fs, event.button, event.time)

    def __popup_menu(self, view, fs):
        return self.__show_menu(view, fs)

    def __show_menu(self, view, fs, button=1, time=0):
        view.grab_focus()
        selection = view.get_selection()
        model, rows = selection.get_selected_rows()
        songs = [self.__cache[model[row][0]] for row in rows]
        menu = self.pm.create_plugins_menu(songs)
        if menu is None: menu = gtk.Menu()
        else: menu.prepend(gtk.SeparatorMenuItem())
        b = gtk.ImageMenuItem(gtk.STOCK_DELETE)
        b.connect('activate', self.__delete,
                  [model[row][0] for row in rows], fs)
        menu.prepend(b)
        menu.show_all()
        menu.popup(None, None, None, button, time)
        return True

    def __delete(self, item, files, fs):
        d = qltk.DeleteDialog(files)
        resp = d.run()
        d.destroy()

        # FIXME: Largely copy/paste from SongList.
        if resp == 1 or resp == gtk.RESPONSE_DELETE_EVENT: return
        else:
            if resp == 0: s = _("Moving %d/%d.")
            elif resp == 2: s = _("Deleting %d/%d.")
            else: return
            w = qltk.WaitLoadWindow(None, len(files), s, (0, len(files)))
            trash = os.path.expanduser("~/.Trash")
            for filename in files:
                try:
                    if resp == 0:
                        basename = os.path.basename(filename)
                        shutil.move(filename, os.path.join(trash, basename))
                    else:
                        os.unlink(filename)

                except:
                    qltk.ErrorMessage(
                        self, _("Unable to delete file"),
                        _("Deleting <b>%s</b> failed. "
                          "Possibly the target file does not exist, "
                          "or you do not have permission to "
                          "delete it.") % (filename)).run()
                    break
                else:
                    w.step(w.current + 1, w.count)
            w.destroy()
            fs.rescan()

    def __changed(self, selector, selection, notebook):
        model, rows = selection.get_selected_rows()
        files = []
        for row in rows:
            filename = model[row][0]
            if not os.path.exists(filename): pass
            elif filename in self.__cache: files.append(self.__cache[filename])
            else: files.append(formats.MusicFile(model[row][0]))
        files = filter(None, files)
        self.emit('changed', files)
        self.__cache.clear()
        if len(files) == 0: self.set_title("Ex Falso")
        elif len(files) == 1:
            self.set_title("%s - Ex Falso" % files[0].comma("title"))
        else:
            self.set_title("%s - Ex Falso" % (_("%(title)s and %(count)d more")
                % {'title': files[0].comma("title"), 'count': len(files) - 1}))
        self.__cache = dict([(song["~filename"], song) for song in files])

gobject.type_register(ExFalsoWindow)
