# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import urllib
import gobject, gtk, pango
import util

from qltk.views import AllTreeView

class DownloadWindow(gtk.Window):
    __window = None

    def download(klass, source, target):
        if klass.__window is None:
            klass.__window = DownloadWindow()
        klass.__window._download(source, target)
        klass.__window.present()
    download = classmethod(download)

    def __init__(self):
        super(DownloadWindow, self).__init__()
        self.set_title("Quod Libet - " + _("Downloads"))
        self.set_default_size(300, 150)
        self.set_border_width(12)
        self.__timeout = None
        model = gtk.ListStore(object, object, int) # fileobjs - source, target
        tv = AllTreeView()
        tv.connect('popup-menu', self.__popup_menu)
        tv.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        tv.set_model(model)
        tv.set_rules_hint(True)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_START)
        column = gtk.TreeViewColumn(_("Filename"), render)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_expand(True)
        def cell_data_name(column, cell, model, iter):
            cell.set_property('text', model[iter][1].name)
        column.set_cell_data_func(render, cell_data_name)
        tv.append_column(column)
        
        render = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Size"), render)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        def cell_data_size(column, cell, model, iter):
            size = util.format_size(model[iter][1].tell())
            cell.set_property('text', size)
        column.set_cell_data_func(render, cell_data_size)
        tv.append_column(column)

        sw = gtk.ScrolledWindow()
        sw.add(tv)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.add(sw)
        self.connect('delete-event', self.__delete_event)
        self.child.show_all()

    def __update(self):
        if self.child is None: return True
        model = self.child.child.get_model()
        for i in range(len(model)):
            model.row_changed((i,), model.get_iter(i))
        return True

    def __popup_menu(self, view):
        selection = view.get_selection()
        model, paths = selection.get_selected_rows()
        if model:
            iters = map(model.get_iter, paths)
            menu = gtk.Menu()
            item = gtk.ImageMenuItem(gtk.STOCK_STOP)
            item.connect_object('activate', self.__stop_download, model, iters)
            menu.append(item)
            menu.connect('selection-done', lambda m: m.destroy())
            menu.show_all()
            menu.popup(None, None, None, 0, gtk.get_current_event_time())
            return True

    def __stop_download(self, model, iters):
        for iter in iters:
            gobject.source_remove(model[iter][2])
            model[iter][0].close()
            model[iter][1].close()
            os.unlink(model[iter][1].name)
            model.remove(iter)

    def present(self):
        super(DownloadWindow, self).present()
        if self.__timeout is None:
            gobject.timeout_add(1000, self.__update)

    def __delete_event(self, window, event):
        self.hide()
        if self.__timeout is not None: gobject.source_remove(self.__timeout)
        self.__timeout = None
        return True

    def _download(self, source, target):
        fileobj = file(target, "wb")
        url = urllib.urlopen(source)
        sock = url.fp._sock
        sock.setblocking(0)
        model = self.child.child.get_model()
        iter = model.append(row=[sock, fileobj, 0])
        sig_id = gobject.io_add_watch(
            sock, gobject.IO_IN|gobject.IO_ERR|gobject.IO_HUP,
            self.__got_data, fileobj, model, iter)
        model[iter][2] = sig_id

    def __got_data(self, src, condition, fileobj, model, iter):
        if condition in [gobject.IO_ERR, gobject.IO_HUP]:
            fileobj.close()
            src.close()
            model.remove(iter)
            return False
        else:
            buf = src.recv(1024*1024)
            if buf: fileobj.write(buf)
            else:
                fileobj.close()
                src.close()
                model.remove(iter)
            return bool(buf)
