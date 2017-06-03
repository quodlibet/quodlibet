# -*- coding: utf-8 -*-
# Copyright 2005, 2009 Joe Wreschnig, Steven Robertson
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os

from gi.repository import Gtk, Pango, GLib

from quodlibet import qltk
from quodlibet import util
from quodlibet import _
from quodlibet.util import connect_obj
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.x import MenuItem
from quodlibet.qltk import Icons
from quodlibet.util.urllib import urlopen


class DownloadWindow(qltk.UniqueWindow):
    downloads = None

    @classmethod
    def download(klass, source, target, parent=None):
        if klass.downloads is None:
            # source fileobj, target fileobj, I/O watch callback ID, source uri
            klass.downloads = Gtk.ListStore(object, object, int, object)
        win = DownloadWindow(parent)
        win.show()
        win._download(source, target)

    def __init__(self, parent=None):
        if self.is_not_unique():
            return
        super(DownloadWindow, self).__init__()
        self.set_title("Quod Libet - " + _("Downloads"))
        self.set_default_size(300, 150)
        self.set_border_width(12)
        self.set_transient_for(qltk.get_top_parent(parent))
        self.__timeout = None

        view = AllTreeView()
        view.connect('popup-menu', self.__popup_menu)
        view.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        view.set_model(self.downloads)
        view.set_rules_hint(True)

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.START)
        column = Gtk.TreeViewColumn(_("Filename"), render)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_expand(True)

        def cell_data_name(column, cell, model, iter, data):
            cell.set_property('text', model[iter][1].name)
        column.set_cell_data_func(render, cell_data_name)
        view.append_column(column)

        render = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_("Size"), render)
        column.set_sizing(Gtk.TreeViewColumnSizing.GROW_ONLY)

        def cell_data_size(column, cell, model, iter, data):
            if model[iter][2] == 0:
                size = _("Queued")
            else:
                size = util.format_size(model[iter][1].tell())
            cell.set_property('text', size)
        column.set_cell_data_func(render, cell_data_size)
        view.append_column(column)

        sw = Gtk.ScrolledWindow()
        sw.add(view)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.add(sw)
        connect_obj(self,
            'delete-event', DownloadWindow.__delete_event, self)
        self.get_child().show_all()

    def __update(self):
        for row in self.downloads:
            self.downloads.row_changed(row.path, row.iter)
        return True

    def __popup_menu(self, view):
        selection = view.get_selection()
        model, paths = selection.get_selected_rows()
        if model:
            iters = map(model.get_iter, paths)
            menu = Gtk.Menu()
            item = MenuItem(_("_Stop"), Icons.PROCESS_STOP)
            connect_obj(item, 'activate', self.__stop_download, iters)
            menu.append(item)
            menu.connect('selection-done', lambda m: m.destroy())
            menu.show_all()
            return view.popup_menu(menu, 0, Gtk.get_current_event_time())

    def __start_next(self):
        started = len([r for r in self.downloads if r[2] != 0])
        iter = self.downloads.get_iter_first()
        while iter is not None:
            if started >= 2:
                break
            if self.downloads[iter][2] == 0:
                url = urlopen(self.downloads[iter][3])
                sock = url.fp._sock
                sock.setblocking(0)
                self.downloads[iter][0] = sock
                sig_id = qltk.io_add_watch(
                    sock, GLib.PRIORITY_DEFAULT,
                    GLib.IO_IN | GLib.IO_ERR | GLib.IO_HUP,
                    self.__got_data, self.downloads[iter][1], iter)
                self.downloads[iter][2] = sig_id
                started += 1
            iter = self.downloads.iter_next(iter)

    def __stop_download(self, iters):
        for iter in iters:
            if self.downloads[iter][2] != 0:
                GLib.source_remove(self.downloads[iter][2])
            if self.downloads[iter][0]:
                self.downloads[iter][0].close()
            self.downloads[iter][1].close()
            os.unlink(self.downloads[iter][1].name)
            self.downloads.remove(iter)
            self.__start_next()

    def present(self):
        super(DownloadWindow, self).present()
        if self.__timeout is None:
            self.__timeout = GLib.timeout_add(1000, self.__update)

    def __delete_event(self, event):
        self.hide()
        if self.__timeout is not None:
            GLib.source_remove(self.__timeout)
        self.__timeout = None
        return True

    def _download(self, source, target):
        # FIXME
        # https://github.com/quodlibet/quodlibet/issues/2401
        return
        fileobj = open(target, "wb")
        self.downloads.append(row=[None, fileobj, 0, source])
        self.__start_next()

    def __got_data(self, src, condition, fileobj, iter):
        if condition in [GLib.IO_ERR, GLib.IO_HUP]:
            fileobj.close()
            src.close()
            self.downloads.remove(iter)
            self.__start_next()
            return False
        else:
            buf = src.recv(1024 * 1024)
            if buf:
                fileobj.write(buf)
            else:
                fileobj.close()
                src.close()
                self.downloads.remove(iter)
                self.__start_next()
            return bool(buf)
