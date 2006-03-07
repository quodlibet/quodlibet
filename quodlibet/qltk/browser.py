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
import util

class LibraryBrowser(Window):
    def __init__(self, Kind, watcher):
        super(LibraryBrowser, self).__init__()
        self.set_border_width(12)
        self.set_title(_("Library Browser"))

        view = SongList(watcher)
        self.add_accel_group(view.accelerators)
        self.songlist = view

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)

        self.browser = browser = Kind(watcher, None)
        browser.connect_object('songs-selected', SongList.set_songs, view)
        if browser.reordered: view.enable_drop()
        if browser.accelerators: self.add_accel_group(browser.accelerators)

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

        view.connect('popup-menu', self.__menu, watcher)
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
        from widgets import main
        from player import playlist as player
        main.playlist.enqueue([view.get_model()[path][0]])
        if player.song is None: player.next()

    def __drag_data_recv(self, view, *args):
        if callable(self.browser.reordered): self.browser.reordered(view)
        view.set_sort_by(None, refresh=False)

    def __cols_changed(self, view, browser):
        for header in view.get_columns():
            tag = header.header_name
            for t in util.tagsplit(tag):
                if t in browser.headers:
                    header.set_visible(True)
                    break
            else: header.set_visible(False)

    def __menu(self, view, watcher):
        path, col = view.get_cursor()
        header = col.header_name
        view.Menu(header, self.browser, watcher).popup(
            None, None, None, 0, gtk.get_current_event_time())
        return True
