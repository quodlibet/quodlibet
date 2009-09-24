# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gtk
import pango

from quodlibet import config
from quodlibet import util

from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.x import Window

class LibraryBrowser(Window):
    def __init__(self, Kind, library):
        super(LibraryBrowser, self).__init__()
        self.set_border_width(6)
        self.set_title("Quod Libet - " + Kind.name)
        self.add(gtk.VBox(spacing=6))
        name = Kind.__name__
        cfg_name = "browser_size_" + name
        try: x, y = map(int, config.get('memory', cfg_name).split())
        except (config.error, ValueError):
            x, y = 500, 300
        screen = self.get_screen()
        x = min(x, screen.get_width())
        y = min(y, screen.get_height())
        self.set_default_size(x, y)
        self.connect('configure-event', LibraryBrowser.__save_size, cfg_name)

        view = SongList(library)
        self.add_accel_group(view.accelerators)
        self.songlist = view

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)

        self.browser = browser = Kind(library, None)
        if browser.reordered:
            view.enable_drop()
        elif browser.dropped:
            view.enable_drop(False)
        if browser.accelerators:
            self.add_accel_group(browser.accelerators)

        self.child.pack_start(browser.pack(sw))

        self.__statusbar = gtk.Label()
        self.__statusbar.set_text(_("No time information"))
        self.__statusbar.set_alignment(1.0, 0.5)
        self.__statusbar.set_ellipsize(pango.ELLIPSIZE_START)
        self.child.pack_end(self.__statusbar, expand=False)

        browser.connect('songs-selected', self.__browser_cb)
        view.connect('popup-menu', self.__menu, library)
        view.connect('drag-data-received', self.__drag_data_recv)
        view.connect('row-activated', self.__enqueue)
        view.get_selection().connect('changed', self.__set_time)
        if browser.headers is not None:
            view.connect('columns-changed', self.__cols_changed, browser)
            self.__cols_changed(view, browser)
        sw.show_all()
        for c in self.child.get_children():
            c.show()
        self.child.show()
        self.show()

    def __browser_cb(self, browser, songs, sorted):
        self.__set_time(songs=songs)
        self.songlist.set_songs(songs, sorted)

    def __enqueue(self, view, path, column):
        from quodlibet.widgets import main
        from quodlibet.player import playlist as player
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

    def __menu(self, view, library):
        path, col = view.get_cursor()
        header = col.header_name
        menu = view.Menu(header, self.browser, library)
        if menu is not None:
            view.popup_menu(menu, 0, gtk.get_current_event_time())
        return True

    def __set_time(self, *args, **kwargs):
        statusbar = self.__statusbar
        songs = kwargs.get("songs") or self.songlist.get_selected_songs()
        if "songs" not in kwargs and len(songs) <= 1:
            songs = self.songlist.get_songs()

        i = len(songs)
        length = sum([song["~#length"] for song in songs])
        t = self.browser.statusbar(i) % {
            'count': i, 'time': util.format_time_long(length)}
        statusbar.set_text(t)

    def __save_size(self, event, cfg_name):
        config.set('memory', cfg_name, '%d %d' %(event.width, event.height))
