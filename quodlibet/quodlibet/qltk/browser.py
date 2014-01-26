# Copyright 2005 Joe Wreschnig, Michael Urman
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Pango

from quodlibet import config
from quodlibet import util
from quodlibet import qltk
from quodlibet import browsers

from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.x import Window, RPaned
from quodlibet.qltk.window import PersistentWindowMixin
from quodlibet.util.library import background_filter


class LibraryBrowser(Window, util.InstanceTracker, PersistentWindowMixin):

    @classmethod
    def open(cls, Kind, library):
        browser = cls(Kind, library)
        browser.show()

    @classmethod
    def save(cls):
        """See which browser windows are open and save their names
        so we can restore them on start.
        """

        names = []
        for browser in cls.instances():
            names.append(browser.name)
        config.set("memory", "open_browsers", "\n".join(names))

    @classmethod
    def restore(cls, library):
        """restore saved browser windows"""

        value = config.get("memory", "open_browsers", "")
        for name in value.split():
            kind = browsers.get(name)
            cls.open(kind, library)

    def __init__(self, Kind, library):
        super(LibraryBrowser, self).__init__(dialog=False)
        self._register_instance()
        self.name = Kind.__name__

        self.set_default_size(600, 400)
        self.enable_window_tracking("browser_" + self.name)
        self.set_border_width(6)
        self.set_title(Kind.name + " - Quod Libet")
        self.add(Gtk.VBox(spacing=6))

        view = SongList(library, update=True)
        view.info.connect("changed", self.__set_time)
        self.songlist = view

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(view)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.browser = browser = Kind(library, False)
        if browser.reordered:
            view.enable_drop()
        elif browser.dropped:
            view.enable_drop(False)
        if browser.accelerators:
            self.add_accel_group(browser.accelerators)

        self.__container = browser.pack(sw)
        self.get_child().pack_start(self.__container, True, True, 0)

        self.__statusbar = Gtk.Label()
        self.__statusbar.set_text(_("No time information"))
        self.__statusbar.set_alignment(1.0, 0.5)
        self.__statusbar.set_ellipsize(Pango.EllipsizeMode.START)
        self.get_child().pack_end(self.__statusbar, False, True, 0)

        browser.connect('songs-selected', self.__browser_cb)
        browser.finalize(False)
        view.connect('popup-menu', self.__menu, library)
        view.connect('drag-data-received', self.__drag_data_recv)
        view.connect('row-activated', self.__enqueue)

        if browser.headers is not None:
            view.connect('columns-changed', self.__cols_changed, browser)
            self.__cols_changed(view, browser)
        sw.show_all()
        for c in self.get_child().get_children():
            c.show()
        self.get_child().show()
        self.__set_pane_size()

    def __set_pane_size(self):
        widgets = qltk.find_widgets(self.__container, RPaned)
        if widgets:
            paned = widgets[0]
            try:
                key = "%s_pos" % self.browser.__class__.__name__
                val = config.getfloat("browsers", key)
            except:
                val = 0.4
            paned.set_relative(val)

    def __browser_cb(self, browser, songs, sorted):
        if browser.background:
            bg = background_filter()
            if bg:
                songs = filter(bg, songs)
        self.songlist.set_songs(songs, sorted)

    def __enqueue(self, view, path, column):
        from quodlibet import app
        app.window.playlist.enqueue([view.get_model()[path][0]])
        if app.player.song is None:
            app.player.next()

    def __drag_data_recv(self, view, *args):
        if callable(self.browser.reordered):
            self.browser.reordered(view)
        view.set_sort_by(None, refresh=False)

    def __cols_changed(self, view, browser):
        for header in view.get_columns():
            tag = header.header_name
            for t in util.tagsplit(tag):
                if t in browser.headers:
                    header.set_visible(True)
                    break
            else:
                header.set_visible(False)

    def __menu(self, view, library):
        path, col = view.get_cursor()
        header = col.header_name
        menu = view.Menu(header, self.browser, library)
        if menu is not None:
            view.popup_menu(menu, 0, Gtk.get_current_event_time())
        return True

    def __set_time(self, info, songs):
        i = len(songs)
        length = sum(song.get("~#length", 0) for song in songs)
        t = self.browser.statusbar(i) % {
            'count': i, 'time': util.format_time_long(length)}
        self.__statusbar.set_text(t)
