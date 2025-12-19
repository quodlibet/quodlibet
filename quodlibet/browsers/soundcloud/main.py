# Copyright 2016-2023 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from urllib.parse import parse_qs, urlparse

from gi.repository import Gtk, Pango

from quodlibet import _
from quodlibet import config, app
from quodlibet import qltk
from quodlibet import util
from quodlibet.browsers import Browser
from quodlibet.qltk import Icons, Message
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.views import RCMHintedTreeView
from quodlibet.qltk.x import Align, ScrolledWindow, WebImage
from quodlibet.util import (
    connect_destroy,
    DeferredSignal,
    website,
    enum,
    cached_property,
)
from quodlibet.util.dprint import print_w, print_d

from .api import SoundcloudApiClient
from .library import SoundcloudLibrary
from .query import SoundcloudQuery
from .util import (
    State,
    FilterType,
    PROCESS_QL_URLS,
    EnterAuthCodeDialog,
    SITE_URL,
    SOUNDCLOUD_NAME,
    sc_btn_image,
)


class SoundcloudBrowser(Browser, util.InstanceTracker):
    background = False
    __librarian = None
    __filter = None

    name = _("Soundcloud Browser")
    accelerated_name = _("Sound_cloud")
    keys = ["Soundcloud"]
    priority = 30
    uses_main_library = False
    headers = (
        "artist ~people title genre ~#length ~mtime ~bitrate date "
        "website comment ~rating "
        "~#playback_count ~#favoritings_count ~#likes_count"
    ).split()

    @enum
    class ModelIndex(int):
        TYPE, ICON_NAME, NAME, QUERY, ALWAYS_ENABLE = range(5)

    login_state = State.LOGGED_OUT

    STAR = [tag for tag in headers if not tag.startswith("~#")]

    @classmethod
    def _init(cls, library):
        cls.__librarian = library.librarian
        cls.filters = [
            (_("Search"), (FilterType.SEARCH, Icons.EDIT_FIND, "", True)),
            # TODO: support for ~#rating=!None etc (#1940)
            (
                _("Favorites"),
                (FilterType.FAVORITES, Icons.FAVORITE, "#(rating = 1.0)", False),
            ),
            (
                _("My tracks"),
                (FilterType.MINE, Icons.MEDIA_RECORD, "soundcloud_user_id=%s", False),
            ),
        ]
        try:
            if cls.library:
                return
        except AttributeError:
            pass
        cls.api_client = SoundcloudApiClient()
        cls.library = SoundcloudLibrary(cls.api_client, app.player)

    @classmethod
    def _destroy(cls):
        cls.__librarian = None
        cls.filters = {}
        cls.library.destroy()
        cls.library = None

    def __inhibit(self):
        self.view.get_selection().handler_block(self.__changed_sig)

    def __uninhibit(self):
        self.view.get_selection().handler_unblock(self.__changed_sig)

    def __destroy(self, *args):
        print_d(f"Destroying Soundcloud Browser {self}")
        if not self.instances():
            self._destroy()

    def __init__(self, library):
        print_d(f"Creating Soundcloud Browser {self}")
        super().__init__(spacing=12)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        if not self.instances():
            self._init(library)
        self._register_instance()

        self.connect("destroy", self.__destroy)
        self.connect("uri-received", self.__handle_incoming_uri)
        connect_destroy(self.api_client, "authenticated", self.__on_authenticated)
        connect_destroy(self.library, "changed", self.__changed)
        self.login_state = State.LOGGED_IN if self.online else State.LOGGED_OUT
        self._create_searchbar(self.library)
        vbox = Gtk.VBox()
        vbox.pack_start(self._create_header(), False, False, 0)
        vbox.pack_start(self._create_category_widget(), True, True, 0)
        vbox.pack_start(self.create_login_button(), False, False, 0)
        vbox.show()
        pane = qltk.ConfigRHPaned("browsers", "soundcloud_pos", 0.4)
        pane.show()
        pane.pack1(vbox, resize=False, shrink=False)
        self._songs_box = songs_box = Gtk.VBox(spacing=6)
        songs_box.pack_start(self._searchbox, False, True, 0)
        songs_box.show()
        pane.pack2(songs_box, resize=True, shrink=False)
        self.pack_start(pane, True, True, 0)
        self.show()

    def menu(self, songs, library, items):
        return SongsMenu(library, songs, edit=False, download=True, items=items)

    @property
    def online(self):
        return self.api_client.online

    def _create_header(self):
        hbox = Gtk.HBox()
        button = Gtk.Button(always_show_image=True, relief=Gtk.ReliefStyle.NONE)
        button.connect("clicked", lambda _: website(SITE_URL))
        button.set_tooltip_text(_("Go to %s") % SITE_URL)
        button.add(self._logo_image)
        hbox.pack_start(button, True, True, 6)
        hbox.show_all()
        return hbox

    def _create_searchbar(self, library):
        completion = LibraryTagCompletion(library)
        self.accelerators = Gtk.AccelGroup()
        search = SearchBarBox(
            completion=completion,
            validator=SoundcloudQuery.validator,
            accel_group=self.accelerators,
            timeout=3000,
        )
        self.__searchbar = search
        search.connect("query-changed", self.__query_changed)

        def focus(widget, *args):
            qltk.get_top_parent(widget).songlist.grab_focus()

        search.connect("focus-out", focus)

        self._searchbox = Align(search, left=0, right=6, top=0)
        self._searchbox.show_all()

    def update_connect_button(self):
        but = self.login_button
        but.set_sensitive(False)
        tooltip, icon = self._login_state_data[self.login_state]
        but.set_tooltip_text(tooltip)
        child = but.get_child()
        if child:
            print_d("Removing old image...")
            but.remove(child)
        but.add(icon if icon else Gtk.Label(tooltip))

        but.get_child().show()
        but.set_sensitive(True)
        but.show()

    def create_login_button(self):
        def clicked_login(*args):
            # TODO: use a magic enum next() method, or similar
            state = self.login_state
            if state == State.LOGGED_IN:
                self.api_client.log_out()
                # Reset the selection, lest it get stuck...
                sel = self.view.get_selection()
                sel.unselect_all()
                first_path = self.view.get_model()[0].path.copy()
                self.view.set_cursor(first_path)
                sel.select_path(first_path)
                self._refresh_online_filters()
                self.login_state = State.LOGGED_OUT
            elif state == State.LOGGING_IN:
                dialog = EnterAuthCodeDialog(app.window)
                value = dialog.run(clipboard=True)
                if value:
                    self.login_state = State.LOGGED_IN
                    print_d(f"Got a user token value of '{value}'")
                    self.api_client.get_tokens(value)
            elif state == State.LOGGED_OUT:
                self.api_client.authenticate_user()
                self.login_state = State.LOGGING_IN
            self.update_connect_button()

        hbox = Gtk.HBox()
        self.login_button = login = Gtk.Button(
            always_show_image=True, relief=Gtk.ReliefStyle.NONE
        )
        self.update_connect_button()
        login.connect("clicked", clicked_login)
        hbox.pack_start(login, True, False, 0)
        hbox.show_all()
        return hbox

    def _create_category_widget(self):
        scrolled_window = ScrolledWindow()
        scrolled_window.show()
        scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
        self.view = view = RCMHintedTreeView()
        view.show()
        view.set_headers_visible(False)
        scrolled_window.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(view)
        model = Gtk.ListStore(int, str, str, str, bool)
        filters = self.filters
        for _i, (name, data) in enumerate(filters):
            filter_type, icon, query, always = data
            enabled = always
            model.append(row=[filter_type, icon, name, query, enabled])

        def search_func(model, column, key, iter, data):
            return key.lower() not in model[iter][column].lower()

        view.set_search_column(self.ModelIndex.NAME)
        view.set_search_equal_func(search_func, None)

        column = Gtk.TreeViewColumn("Songs")
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        renderpb = Gtk.CellRendererPixbuf()
        renderpb.props.xpad = 6
        renderpb.props.ypad = 6
        column.pack_start(renderpb, False)
        column.add_attribute(renderpb, "icon-name", self.ModelIndex.ICON_NAME)
        render = Gtk.CellRendererText()
        render.set_property("ellipsize", Pango.EllipsizeMode.END)

        def cdf(column, cell, model, iter_, user_data):
            on = (
                self.login_state == State.LOGGED_IN
                or model[iter_][self.ModelIndex.ALWAYS_ENABLE]
            )
            cell.set_sensitive(on)

        column.set_cell_data_func(render, cdf)
        column.set_cell_data_func(renderpb, cdf)

        view.append_column(column)
        column.pack_start(render, True)
        column.add_attribute(render, "text", self.ModelIndex.NAME)
        view.set_model(model)

        selection = view.get_selection()

        def select_func(sel, model, path, value):
            return (
                self.login_state == State.LOGGED_IN
                or model[model.get_iter(path)][self.ModelIndex.ALWAYS_ENABLE]
            )

        selection.set_select_function(select_func)
        selection.select_iter(model.get_iter_first())
        self._refresh_online_filters()
        self.__changed_sig = connect_destroy(
            selection, "changed", DeferredSignal(self._on_select)
        )
        return scrolled_window

    def _on_select(self, sel):
        model, paths = sel.get_selected_rows()
        if not paths:
            return
        row = model[paths[0]]
        query_text = row[self.ModelIndex.QUERY]
        filter_type = row[self.ModelIndex.TYPE]

        if filter_type == FilterType.SEARCH:
            self.__searchbar.set_enabled()
        elif filter_type == FilterType.FAVORITES:
            print_d("Getting favorites...")
            self.api_client.get_favorites()
            self.__searchbar.set_enabled(False)
        elif filter_type == FilterType.MINE:
            print_d("Getting user tracks...")
            self.api_client.get_my_tracks()
            self.__searchbar.set_enabled(False)
            query_text = query_text % self.api_client.user_id

        self.__searchbar.set_text(query_text)
        self.activate()

    def pack(self, songpane):
        container = Gtk.VBox()
        container.add(self)
        self._songs_box.add(songpane)
        return container

    def unpack(self, container, songpane):
        self._songs_box.remove(songpane)
        container.remove(self)

    def __changed(self, library, songs):
        print_d(f"Updating view for {len(songs)} song(s)")
        self.activate()

    def __query_changed(self, bar, text, restore=False):
        try:
            self.__filter = SoundcloudQuery(text, self.STAR)
            self.library.query_with_refresh(self.__filter)
        except SoundcloudQuery.Error as e:
            print_d(f"Couldn't parse query: {e}")
        else:
            print_d(f"Got terms from query {text!r}: {self.__filter.terms}")
            if not restore:
                self.activate()

    def __get_selected_libraries(self):
        """Returns the libraries to search in depending on the
        filter selection"""

        return [self.library]

    def restore(self):
        filter_type = config.getint(
            "browsers", "soundcloud_selection", FilterType.SEARCH
        )
        model = self.view.get_model()
        it = model.get_iter_first()
        while it:
            if model.get_value(it, 0) == filter_type:
                break
            it = model.iter_next(it)

        if filter_type == FilterType.SEARCH:
            self.__searchbar.set_enabled()
            self.__inhibit()

        self.view.get_selection().select_iter(it)
        self.__uninhibit()

        text = config.gettext("browsers", "query_text")
        self.__searchbar.set_text(text)
        self.__query_changed(None, text, restore=True)

    def __get_filter(self):
        return self.__filter or SoundcloudQuery("")

    def can_filter_text(self):
        return True

    def filter_text(self, text):
        model = self.view.get_model()
        it = model.get_iter_first()
        selected = False
        while it:
            typ = model.get_value(it, 0)
            if typ == FilterType.SEARCH:
                search_it = it
            elif (typ == FilterType.FAVORITES and text == "#(rating = 1.0)") or (
                typ == FilterType.MINE
                and text == f"soundcloud_user_id={self.api_client.user_id}"
            ):
                self.view.get_selection().select_iter(it)
                selected = True
                break
            it = model.iter_next(it)

        if not selected:
            # We don't want the selection to be cleared, so inhibit
            # the selection callback method
            self.__inhibit()
            self.view.get_selection().select_iter(search_it)
            self.__uninhibit()

            self.__searchbar.set_enabled()
            self.__searchbar.set_text(text)
            self.__query_changed(None, text)

            if SoundcloudQuery(text).is_parsable:
                self.activate()
            else:
                print_d(f"Not parsable: {text}")

    def get_filter_text(self):
        return self.__searchbar.get_text()

    def activate(self):
        print_d(f'Refreshing browser for query "{self.__filter!r}"')
        songs = self.library.query(self.get_filter_text())
        self.songs_selected(songs)

    def active_filter(self, song):
        for lib in self.__get_selected_libraries():
            if song in lib:
                filter_ = self.__get_filter()
                if filter_:
                    return filter_.search(song)
                return True
        else:
            return False

    def save(self):
        text = self.__searchbar.get_text()
        config.settext("browsers", "query_text", text)
        self.api_client.save_auth()

        model, paths = self.view.get_selection().get_selected_rows()
        if paths:
            row = model[paths[0]]
            filter_type = row[self.ModelIndex.TYPE]
            config.set("browsers", "soundcloud_selection", filter_type)

    def _refresh_online_filters(self):
        model = self.view.get_model()
        for row in model:
            model.row_changed(row.path, model.get_iter(row.path))

    def __handle_incoming_uri(self, obj, uri):
        if not PROCESS_QL_URLS:
            print_w(f"Processing of quodlibet:// URLs is disabled. ({uri})")
            return
        uri = urlparse(uri)
        if (
            uri.scheme == "quodlibet"
            and uri.netloc == "callbacks"
            and uri.path == "/soundcloud"
        ):
            try:
                code = parse_qs(uri.query)["code"][0]
            except IndexError:
                print_w(f"Malformed response in callback URI: {uri}")
                return
            print_d(f"Processing Soundcloud callback ({uri})")
            self.api_client.get_tokens(code)
        else:
            print_w(f"Unknown URL format ({uri})")

    def __on_authenticated(self, obj, data):
        name = data.username
        self.login_state = State.LOGGED_IN
        self.update_connect_button()
        self.activate()
        msg = Message(
            Gtk.MessageType.INFO,
            app.window,
            _("Connected"),
            _("Quod Libet is now connected, %s!") % name,
        )
        msg.run()

    @cached_property
    def _logo_image(self):
        return WebImage(
            "https://developers.soundcloud.com/assets/logo_black.png", 104, 16
        )

    @cached_property
    def _login_state_data(self):
        """Login-state-based data for configuring actions (e.g. the button)"""
        return {
            State.LOGGED_IN: (
                _("Log out of %s") % SOUNDCLOUD_NAME,
                sc_btn_image("disconnect-l", 140, 29),
            ),
            State.LOGGING_IN: (_("Enter code…"), None),
            State.LOGGED_OUT: (
                _("Log in to %s") % SOUNDCLOUD_NAME,
                sc_btn_image("connect-l", 124, 29),
            ),
        }
