# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import gtk
import pango

from quodlibet import config
from quodlibet import util

from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.x import Window, RPaned
from quodlibet.qltk.window import PersistentWindowMixin
from quodlibet.util.library import background_filter


class LibraryBrowser(Window, PersistentWindowMixin):
    def __init__(self, Kind, library):
        super(LibraryBrowser, self).__init__(dialog=False)
        self.set_default_size(600, 400)
        self.enable_window_tracking("browser_" + Kind.__name__)
        self.set_border_width(6)
        self.set_title(Kind.name + " - Quod Libet")
        self.add(gtk.VBox(spacing=6))

        view = SongList(library, update=True)
        self.add_accel_group(view.accelerators)
        self.songlist = view

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.add(view)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)

        self.browser = browser = Kind(library, False)
        if browser.reordered:
            view.enable_drop()
        elif browser.dropped:
            view.enable_drop(False)
        if browser.accelerators:
            self.add_accel_group(browser.accelerators)

        self.__container = browser.pack(sw)
        self.child.pack_start(self.__container)

        self.__statusbar = gtk.Label()
        self.__statusbar.set_text(_("No time information"))
        self.__statusbar.set_alignment(1.0, 0.5)
        self.__statusbar.set_ellipsize(pango.ELLIPSIZE_START)
        self.child.pack_end(self.__statusbar, expand=False)

        browser.connect('songs-selected', self.__browser_cb)
        browser.finalize(False)
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
        self.__set_pane_size()

    def __set_pane_size(self):
        sub = self.__container
        if not isinstance(self.__container, RPaned):
            for child in self.__container.get_children():
                if isinstance(child, RPaned):
                    sub = child

        if isinstance(sub, RPaned):
            try:
                key = "%s_pos" % self.browser.__class__.__name__
                val = config.getfloat("browsers", key)
            except:
                val = 0.4
            sub.set_relative(val)

    def __browser_cb(self, browser, songs, sorted):
        if browser.background:
            bg = background_filter()
            if bg: songs = filter(bg, songs)
        self.__set_time(songs=songs)
        self.songlist.set_songs(songs, sorted)

    def __enqueue(self, view, path, column):
        from quodlibet import app
        app.window.playlist.enqueue([view.get_model()[path][0]])
        if app.player.song is None: app.player.next()

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
        length = sum([song.get("~#length", 0) for song in songs])
        t = self.browser.statusbar(i) % {
            'count': i, 'time': util.format_time_long(length)}
        statusbar.set_text(t)
