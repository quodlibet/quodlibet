# Copyright 2005, 2009 Joe Wreschnig, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import urllib

import gobject
import gtk
import pango

from quodlibet import qltk
from quodlibet import util

from quodlibet.qltk.views import AllTreeView

class DownloadWindow(qltk.UniqueWindow):
    downloads = None

    def download(klass, source, target, parent=None):
        if klass.downloads is None:
            # source fileobj, target fileobj, I/O watch callback ID, source uri
            klass.downloads = gtk.ListStore(object, object, int, object)
        win = DownloadWindow(parent)
        win._download(source, target)
    download = classmethod(download)

    def __init__(self, parent=None):
        if self.is_not_unique(): return
        super(DownloadWindow, self).__init__()
        self.set_title("Quod Libet - " + _("Downloads"))
        self.set_default_size(300, 150)
        self.set_border_width(12)
        self.set_transient_for(qltk.get_top_parent(parent))
        self.__timeout = None

        view = AllTreeView()
        view.connect('popup-menu', self.__popup_menu)
        view.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        view.set_model(self.downloads)
        view.set_rules_hint(True)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_START)
        column = gtk.TreeViewColumn(_("Filename"), render)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_expand(True)
        def cell_data_name(column, cell, model, iter):
            cell.set_property('text', model[iter][1].name)
        column.set_cell_data_func(render, cell_data_name)
        view.append_column(column)

        render = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Size"), render)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        def cell_data_size(column, cell, model, iter):
            if model[iter][2] == 0: size = _("Queued")
            else: size = util.format_size(model[iter][1].tell())
            cell.set_property('text', size)
        column.set_cell_data_func(render, cell_data_size)
        view.append_column(column)

        sw = gtk.ScrolledWindow()
        sw.add(view)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.add(sw)
        self.connect_object(
            'delete-event', DownloadWindow.__delete_event, self)
        self.show_all()

    def __update(self):
        for row in self.downloads:
            self.downloads.row_changed(row.path, row.iter)
        return True

    def __popup_menu(self, view):
        selection = view.get_selection()
        model, paths = selection.get_selected_rows()
        if model:
            iters = map(model.get_iter, paths)
            menu = gtk.Menu()
            item = gtk.ImageMenuItem(gtk.STOCK_STOP)
            item.connect_object('activate', self.__stop_download, iters)
            menu.append(item)
            menu.connect('selection-done', lambda m: m.destroy())
            menu.show_all()
            return view.popup_menu(menu, 0, gtk.get_current_event_time())

    def __start_next(self):
        started = len(filter(lambda row: row[2] != 0, self.downloads))
        iter = self.downloads.get_iter_root()
        while iter is not None:
            if started >= 2: break
            if self.downloads[iter][2] == 0:
                url = urllib.urlopen(self.downloads[iter][3])
                sock = url.fp._sock
                sock.setblocking(0)
                self.downloads[iter][0] = sock
                sig_id = gobject.io_add_watch(
                    sock, gobject.IO_IN|gobject.IO_ERR|gobject.IO_HUP,
                    self.__got_data, self.downloads[iter][1], iter)
                self.downloads[iter][2] = sig_id
                started += 1
            iter = self.downloads.iter_next(iter)

    def __stop_download(self, iters):
        for iter in iters:
            if self.downloads[iter][2] != 0:
                gobject.source_remove(self.downloads[iter][2])
            if self.downloads[iter][0]:
                self.downloads[iter][0].close()
            self.downloads[iter][1].close()
            os.unlink(self.downloads[iter][1].name)
            self.downloads.remove(iter)
            self.__start_next()

    def present(self):
        super(DownloadWindow, self).present()
        if self.__timeout is None:
            self.__timeout = gobject.timeout_add(1000, self.__update)

    def __delete_event(self, event):
        self.hide()
        if self.__timeout is not None:
            gobject.source_remove(self.__timeout)
        self.__timeout = None
        return True

    def _download(self, source, target):
        fileobj = file(target, "wb")
        self.downloads.append(row=[None, fileobj, 0, source])
        self.__start_next()

    def __got_data(self, src, condition, fileobj, iter):
        if condition in [gobject.IO_ERR, gobject.IO_HUP]:
            fileobj.close()
            src.close()
            self.downloads.remove(iter)
            self.__start_next()
            return False
        else:
            buf = src.recv(1024*1024)
            if buf: fileobj.write(buf)
            else:
                fileobj.close()
                src.close()
                self.downloads.remove(iter)
                self.__start_next()
            return bool(buf)
