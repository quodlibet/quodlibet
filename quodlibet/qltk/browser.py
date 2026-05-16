# Copyright 2005 Joe Wreschnig, Michael Urman
#        2016-25 Nick Boultbee
#           2018 Peter Strulo
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from gi.repository import GLib, Gio, Gtk, Pango

from quodlibet import config, print_d
from quodlibet import util
from quodlibet import browsers
from quodlibet import app
from quodlibet import _

from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.x import ScrolledWindow
from quodlibet.qltk.window import Window, PersistentWindowMixin
from quodlibet.util.library import background_filter


class FilterMenu:
    """Provides the "Filters" submenu plus its action group.

    When ``action_group`` is passed in, the menu adds its actions to it (so
    callers can plug the resulting ``menu_model`` into their own menubar).
    Otherwise FilterMenu owns a standalone action group.
    """

    def __init__(self, library, player, action_group=None):
        self._browser = None
        self._library = library
        self._player = player
        self._standalone = action_group is None
        ag = action_group if action_group is not None else Gio.SimpleActionGroup()
        self._action_group = ag

        actions: dict[str, Gio.SimpleAction] = {}

        def add(name, handler=None):
            act = Gio.SimpleAction.new(name, None)
            if handler is not None:
                act.connect("activate", handler)
            ag.add_action(act)
            actions[name] = act
            return act

        add("PlayedRecently", lambda *a: self._make_query("#(lastplayed < 7 days ago)"))
        add("AddedRecently", lambda *a: self._make_query("#(added < 7 days ago)"))
        add("TopRated", self.__top_rated)
        add("All", lambda *a: self._browser and self._browser.unfilter())

        for tag_ in ("genre", "artist", "album"):
            add(f"Filter{util.capitalize(tag_)}", self.__filter_on(tag_, player))
            add(f"Random{util.capitalize(tag_)}", self.__random(tag_))

        self._actions = actions

        # Build the menu model
        menu = Gio.Menu()
        sec = Gio.Menu()
        sec.append(_("On Current _Genre(s)"), "win.FilterGenre")
        sec.append(_("On Current _Artist(s)"), "win.FilterArtist")
        sec.append(_("On Current Al_bum"), "win.FilterAlbum")
        menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append(_("Random _Genre"), "win.RandomGenre")
        sec.append(_("Random _Artist"), "win.RandomArtist")
        sec.append(_("Random Al_bum"), "win.RandomAlbum")
        menu.append_section(None, sec)
        sec = Gio.Menu()
        sec.append(_("All _Songs"), "win.All")
        sec.append(_("Recently _Played"), "win.PlayedRecently")
        sec.append(_("Recently _Added"), "win.AddedRecently")
        top_rated = Gio.MenuItem.new(_("_Top 40"), "win.TopRated")
        top_rated.set_attribute_value(
            "tooltip",
            GLib.Variant.new_string(
                _(
                    "The 40 songs you've played most (more than 40 may "
                    "be chosen if there are ties)"
                )
            ),
        )
        sec.append_item(top_rated)
        menu.append_section(None, sec)
        self.menu_model = menu

        self._player_id = player.connect("song-started", self._on_song_started)
        self.set_song(player.song)
        self._hide_menus()

    def destroy(self):
        if self._player:
            self._player.disconnect(self._player_id)
        self._player = None
        self._browser = None
        self._library = None

    def _on_song_started(self, player, song):
        self.set_song(song)

    def __random(self, key):
        def cb(*args):
            if self._browser:
                self._browser.filter_random(key)

        return cb

    def __filter_on(self, header, player):
        def cb(*args):
            if not self._browser:
                return
            songs = [player.song] if player.song else None
            if not songs:
                return
            self._browser.filter_on(songs, header)

        return cb

    def __top_rated(self, *args):
        bg = background_filter()
        songs = (bg and filter(bg, self._library)) or self._library
        songs = [song.get("~#playcount", 0) for song in songs]
        if not songs:
            return
        songs.sort()
        if len(songs) < 40:
            self._make_query(f"#(playcount > {songs[0] - 1:d})")
        else:
            self._make_query(f"#(playcount > {songs[-40] - 1:d})")

    def _make_query(self, query):
        assert isinstance(query, str)
        if self._browser.can_filter_text():
            self._browser.filter_text(query)
            self._browser.activate()

    def _hide_menus(self):
        # Gio.Menu items don't support hide; instead, we disable filter
        # actions that don't apply to the current browser.
        menus = {
            "genre": ["FilterGenre", "RandomGenre"],
            "artist": ["FilterArtist", "RandomArtist"],
            "album": ["FilterAlbum", "RandomAlbum"],
            None: ["PlayedRecently", "AddedRecently", "TopRated", "All"],
        }
        for key, names in menus.items():
            can = bool(self._browser and self._browser.can_filter(key))
            for name in names:
                self._actions[name].set_enabled(can)

    def set_browser(self, browser):
        self._browser = browser
        self._hide_menus()

    def set_song(self, song):
        for name in ("FilterAlbum", "FilterArtist", "FilterGenre"):
            self._actions[name].set_enabled(bool(song))
        if song:
            for h in ("genre", "artist", "album"):
                self._actions[f"Filter{util.capitalize(h)}"].set_enabled(h in song)

    @property
    def action_group(self):
        return self._action_group


class LibraryBrowser(Window, util.InstanceTracker, PersistentWindowMixin):
    @classmethod
    def open(cls, browser_cls, library, player):
        """Creates and shows a new browser instance"""

        browser = cls(browser_cls, library, player)
        browser.show()
        return browser

    @classmethod
    def save(cls):
        """See which browser windows are open and save their names
        so we can restore them on start.
        """

        config.set(
            "memory",
            "open_browsers",
            "\n".join(browser.name for browser in cls.instances()),
        )

    @classmethod
    def restore(cls, library, player):
        """restore saved browser windows"""

        value = config.get("memory", "open_browsers", "")
        for name in value.split():
            kind = browsers.get(name)
            browser = cls(kind, library, player)
            browser.show_maybe()

    def __init__(self, browser_cls, library, player):
        super().__init__(dialog=False)
        self._register_instance()
        self.name = browser_cls.__name__

        self.set_default_size(600, 400)
        self.enable_window_tracking("browser_" + self.name)
        self.set_title(browser_cls.name + " - Quod Libet")
        self.add(
            Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
            )
        )

        view = SongList(library, update=True)
        view.info.connect("changed", self.__set_totals)
        self.songlist = view
        self.songlist.sortable = not browser_cls.can_reorder

        sw = ScrolledWindow()
        sw.set_child(view)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.browser = browser = browser_cls(library)
        if browser.can_reorder:
            view.enable_drop()
        elif browser.dropped:
            view.enable_drop(False)
        if browser.accelerators:
            self.add_accel_group(browser.accelerators)

        self.__container = browser.pack(sw)
        self.get_child().prepend(self.__container)

        main = self.get_child()
        bottom = Gtk.Box()
        main.append(bottom)

        self._filter_menu = filter_menu = FilterMenu(library, player)
        filter_menu.set_browser(self.browser)
        self.insert_action_group("win", filter_menu.action_group)
        outer = Gio.Menu()
        outer.append_submenu(_("_Filters"), filter_menu.menu_model)
        filter_button = Gtk.MenuButton.new()
        filter_button.set_menu_model(outer)
        filter_button.set_label(_("_Filters"))
        filter_button.set_use_underline(True)
        bottom.prepend(filter_button)

        self.__statusbar = Gtk.Label()
        self.__statusbar.set_xalign(1.0)
        self.__statusbar.set_yalign(0.5)
        # GTK4: set_padding() removed, use margins
        self.__statusbar.set_margin_start(6)
        self.__statusbar.set_margin_end(6)
        self.__statusbar.set_margin_top(3)
        self.__statusbar.set_margin_bottom(3)
        self.__statusbar.set_ellipsize(Pango.EllipsizeMode.START)
        bottom.append(self.__statusbar)
        self.__statusbar.show()
        bottom.show()

        browser.connect("songs-selected", self.__browser_cb)
        browser.finalize(False)
        view.connect("popup-menu", self._menu, library)
        view.connect("drag-data-received", self.__drag_data_recv)
        view.connect("row-activated", self.__enqueue, player)

        if browser.headers is not None:
            view.connect("columns-changed", self.__cols_changed, browser)
            self.__cols_changed(view, browser)
        sw.show_all()
        # GTK4: get_children() removed, use helper
        from quodlibet.qltk import get_children

        for c in get_children(self.get_child()):
            c.show()
        self.get_child().show()

        self.connect("destroy", self._on_destroy)

    def _on_destroy(self, *args):
        # GTK4: self.destroy() removed - _filter_menu cleaned up automatically
        pass

    def __browser_cb(self, browser, songs, sorted):
        if browser.background:
            bg = background_filter()
            if bg:
                songs = list(filter(bg, songs))
        print_d(f"Setting {len(songs)} songs...")
        self.songlist.set_songs(songs, sorted)

    def __enqueue(self, view, path, column, player):
        app.window.playlist.enqueue([view.get_model()[path][0]])
        if player.song is None:
            player.next()

    def __drag_data_recv(self, view, *args):
        if self.browser.can_reorder:
            songs = view.get_songs()
            self.browser.reordered(songs)
        view.clear_sort()

    def __cols_changed(self, view, browser):
        for header in view.get_columns():
            tag = header.header_name
            for t in util.tagsplit(tag):
                if t in browser.headers:
                    header.set_visible(True)
                    break
            else:
                header.set_visible(False)

    def _menu(self, view: SongList, library) -> bool:
        path, col = view.get_cursor()
        header = col.header_name
        menu = view.menu(header, self.browser, library)
        if menu is not None:
            view.popup_menu(menu, 0, GLib.CURRENT_TIME)
        return True

    def __set_totals(self, info, songs):
        i = len(songs)
        length = sum(song.get("~#length", 0) for song in songs)
        t = self.browser.status_text(count=i, time=util.format_time_preferred(length))
        self.__statusbar.set_text(t)
