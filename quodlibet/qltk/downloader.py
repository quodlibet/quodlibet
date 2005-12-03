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
        model = gtk.ListStore(str, int)
        tv = gtk.TreeView()
        tv.set_model(model)
        tv.set_rules_hint(True)

        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        column = gtk.TreeViewColumn(_("Filename"), render, text=0)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        column.set_expand(True)
        tv.append_column(column)
        
        render = gtk.CellRendererText()
        column = gtk.TreeViewColumn(_("Size"), render)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        def cell_data(column, cell, model, iter):
            size = util.format_size(model[iter][1])
            render.set_property('text', size)
        column.set_cell_data_func(render, cell_data)
        tv.append_column(column)

        sw = gtk.ScrolledWindow()
        sw.add(tv)
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.add(sw)
        self.connect('delete-event', self.__delete_event)
        self.child.show_all()

    def __delete_event(self, window, event):
        self.hide()
        return True

    def _download(self, source, target):
        fileobj = file(target, "wb")
        url = urllib.urlopen(source)
        sock = url.fp._sock
        sock.setblocking(0)
        model = self.child.child.get_model()
        iter = model.append(row=[os.path.basename(target), 0])
        gobject.io_add_watch(sock, gobject.IO_IN|gobject.IO_ERR|gobject.IO_HUP,
                             self.__got_data, fileobj, model, iter)

    def __got_data(self, src, condition, fileobj, model, iter):
        if condition in [gobject.IO_ERR, gobject.IO_HUP]:
            fileobj.close()
            src.close()
            model.remove(iter)
            return False
        else:
            buf = src.recv(1024*1024)
            if buf:
                model[iter][1] += len(buf)
                model.row_changed(model.get_path(iter), iter)
                fileobj.write(buf)
                return True
            else:
                fileobj.close()
                src.close()
                model.remove(iter)
                return False

            
