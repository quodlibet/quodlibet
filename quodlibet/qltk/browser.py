# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk
from qltk.x import Window
from qltk.songlist import SongList

class LibraryBrowser(Window):
    def __init__(self, Kind, watcher):
        super(LibraryBrowser, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Library Browser"))

        view = SongList(watcher)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)

        self.browser = browser = Kind(watcher, None)
        browser.connect_object('songs-selected', SongList.set_songs, view)
        if browser.reordered: view.enable_drop()

        if Kind.expand:
            container = Kind.expand()
            container.pack1(browser, resize=True)
            container.pack2(sw, resize=True)
            self.add(container)
        else:
            vbox = gtk.VBox(spacing=6)
            vbox.pack_start(browser, expand=False)
            vbox.pack_start(sw)
            self.add(vbox)

        view.connect('button-press-event', self.__button_press, watcher)
        view.connect('popup-menu', self.__menu, 3, 0, watcher)
        view.connect('drag-data-received', self.__drag_data_recv)
        view.connect('row-activated', self.__enqueue)
        if browser.headers is not None:
            view.connect('columns-changed', self.__cols_changed, browser)
            self.__cols_changed(view, browser)
        self.set_default_size(500, 300)
        sw.show_all()
        self.child.show()
        self.show()

    def __enqueue(self, view, path, column):
        from widgets import widgets
        widgets.main.playlist.enqueue([view.get_model()[path][0]])

    def __drag_data_recv(self, view, *args):
        if callable(self.browser.reordered): self.browser.reordered(view)
        view.set_sort_by(None, refresh=False)

    def __cols_changed(self, view, browser):
        for header in view.get_columns():
            tag = header.header_name
            if "~" in tag[1:]: tag = filter(None, tag.split("~"))[0]
            header.set_visible(tag in browser.headers)

    def __button_press(self, view, event, watcher):
        if event.button != 3: return False
        x, y = map(int, [event.x, event.y])
        try: path, col, cellx, celly = view.get_path_at_pos(x, y)
        except TypeError: return True
        view.grab_focus()
        selection = view.get_selection()
        if not selection.path_is_selected(path):
            view.set_cursor(path, col, 0)
        self.__menu(view, event.button, event.time, watcher)
        return True

    def __menu(self, view, button, time, watcher):
        path, col = view.get_cursor()
        header = col.header_name
        view.Menu(header, self.browser, watcher).popup(
            None, None, None, button, time)
        return True

