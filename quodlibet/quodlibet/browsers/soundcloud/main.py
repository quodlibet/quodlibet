# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from gi.repository import Gtk, Pango
from urlparse import parse_qs

from quodlibet import config, print_d, print_w, app
from quodlibet import qltk
from quodlibet import util
from quodlibet.browsers import Browser
from quodlibet.browsers.soundcloud.api import SoundcloudApiClient
from quodlibet.browsers.soundcloud.library import SoundcloudLibrary
from quodlibet.browsers.soundcloud.util import SITE_URL, LOGO_IMAGE_BLACK, \
    LOGIN_IMAGES
from quodlibet.qltk import Icons, Message
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.menubutton import MenuButton
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.x import Align, ScrolledWindow
from quodlibet.qltk.x import SymbolicIconImage
from quodlibet.query import Query
from quodlibet.util import connect_destroy, DeferredSignal, website
from quodlibet.util.uri import URI


class SoundcloudBrowser(Browser, util.InstanceTracker):

    background = False
    __librarian = None
    __filter = None

    name = _("Soundcloud Browser")
    accelerated_name = _("Sound_cloud")
    keys = ["Soundcloud"]
    priority = 30
    uses_main_library = False
    headers = ("artist ~people title genre ~#length ~mtime ~bitrate date "
               "website comment ~rating "
               "~#playback_count ~#likes_count").split()

    class ModelIndex(object):
        TYPE, ICON_NAME, KEY, NAME = range(4)

    class FilterType(object):
        SEARCH, TYPE_ALL, SEP = range(3)

    STAR = [tag for tag in headers if not tag.startswith("~#")]

    @classmethod
    def _init(klass, library):
        klass.__librarian = library.librarian
        klass.filters = {"All": Query("", star=klass.STAR)}
        token = config.get("browsers", "soundcloud_token", default=None)
        try:
            if klass.library:
                return
        except AttributeError:
            pass
        klass.api_client = SoundcloudApiClient(token)
        klass.library = SoundcloudLibrary(klass.api_client, app.player)

    @classmethod
    def _destroy(klass):
        klass.__librarian = None
        klass.filters = {}
        klass.library.destroy()
        klass.library = None

    def __inhibit(self):
        self.view.get_selection().handler_block(self.__changed_sig)

    def __uninhibit(self):
        self.view.get_selection().handler_unblock(self.__changed_sig)

    def __destroy(self, *args):
        self.api_client.disconnect(self.__auth_sig)
        if not self.instances():
            self._destroy()

    def __init__(self, library):
        super(SoundcloudBrowser, self).__init__(spacing=12)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        if not self.instances():
            self._init(library)
        self._register_instance()

        self.connect('destroy', self.__destroy)
        self.connect('uri-received', self.__handle_incoming_uri)
        self.__auth_sig = self.api_client.connect('authenticated',
                                                  self.__on_authenticated)

        self._create_searchbar(library)

        vbox = Gtk.VBox()
        vbox.pack_start(self._create_footer(), False, False, 6)
        vbox.pack_start(self._create_category_widget(), True, True, 0)
        vbox.pack_start(self.create_login_button(), False, False, 6)
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

    def _create_footer(self):
        hbox = Gtk.HBox()
        button = Gtk.Button(always_show_image=True,
                            relief=Gtk.ReliefStyle.NONE)
        button.connect('clicked', lambda _: website(SITE_URL))
        # button.set_tooltip_text(_("Go to %s" % SITE_URL))
        button.add(LOGO_IMAGE_BLACK)
        hbox.pack_start(button, True, True, 6)
        hbox.show_all()
        return hbox

    def _create_searchbar(self, library):
        completion = LibraryTagCompletion(library)
        self.accelerators = Gtk.AccelGroup()
        self.__searchbar = search = SearchBarBox(completion=completion,
                                                 accel_group=self.accelerators,
                                                 timeout=3000)
        search.connect('query-changed', self.__filter_changed)

        def focus(widget, *args):
            qltk.get_top_parent(widget).songlist.grab_focus()
        search.connect('focus-out', focus)

        self._searchbox = Align(search, left=0, right=6, top=6)
        self._searchbox.show_all()

    def _create_prefs_button(self, menu):
        prefs_button = MenuButton(
            SymbolicIconImage(Icons.EMBLEM_SYSTEM, Gtk.IconSize.MENU),
            arrow=True)
        prefs_button.set_menu(menu)
        return prefs_button

    def update_connect_button(self, online):
        but = self.login_button
        but.set_sensitive(False)
        but.set_tooltip_text((_("Log out of %s") if online
                              else _("Log in to %s")) % "soundcloud")
        image = but.get_child()
        if image:
            print_d("Removing old image...")
            but.remove(image)
        but.add(LOGIN_IMAGES[online])
        but.get_child().show()
        but.set_sensitive(True)
        but.show()

    def create_login_button(self):
        def clicked_login(*args):
            if self.api_client.online:
                self.api_client.log_out()
            else:
                self.api_client.authenticate_user()
            self.update_connect_button(self.api_client.online)

        hbox = Gtk.HBox()
        self.login_button = login = Gtk.Button(always_show_image=True,
                                               relief=Gtk.ReliefStyle.NONE)
        self.update_connect_button(self.api_client.online)
        login.connect('clicked', clicked_login)
        hbox.pack_start(login, True, False, 0)
        hbox.show_all()
        return hbox

    def _create_category_widget(self):
        scrolled_window = ScrolledWindow()
        scrolled_window.show()
        scrolled_window.set_shadow_type(Gtk.ShadowType.IN)
        self.view = view = AllTreeView()
        view.show()
        view.set_headers_visible(False)
        scrolled_window.set_policy(
            Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled_window.add(view)
        model = Gtk.ListStore(int, str, str, str)
        model.append(row=[self.FilterType.SEP, Icons.FOLDER, "", ""])
        filters = self.filters
        for name, query in sorted(filters.iteritems()):
            model.append(row=[self.FilterType.SEARCH,
                              Icons.EDIT_FIND,
                              name,
                              name])

        def is_separator(model, iter, data):
            return model[iter][self.ModelIndex.TYPE] == self.FilterType.SEP
        view.set_row_separator_func(is_separator, None)

        def search_func(model, column, key, iter, data):
            return key.lower() not in model[iter][column].lower()

        view.set_search_column(self.ModelIndex.NAME)
        view.set_search_equal_func(search_func, None)
        column = Gtk.TreeViewColumn("genres")
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        renderpb = Gtk.CellRendererPixbuf()
        renderpb.props.xpad = 3
        column.pack_start(renderpb, False)
        column.add_attribute(renderpb, "icon-name", self.ModelIndex.ICON_NAME)
        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        view.append_column(column)
        column.pack_start(render, True)
        column.add_attribute(render, "text", self.ModelIndex.NAME)
        view.set_model(model)

        # Selection
        selection = view.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        activate = DeferredSignal(lambda _: self.activate())
        self.__changed_sig = connect_destroy(selection, 'changed', activate)
        return scrolled_window

    def pack(self, songpane):
        container = Gtk.VBox()
        container.add(self)
        self._songs_box.add(songpane)
        return container

    def unpack(self, container, songpane):
        self._songs_box.remove(songpane)
        container.remove(self)

    def __filter_changed(self, bar, text, restore=False):
        self.__filter = Query(text, self.STAR)
        if not restore:
            self.activate()

    def __get_selected_libraries(self):
        """Returns the libraries to search in depending on the
        filter selection"""

        return [self.library]

    def restore(self):
        text = config.get("browsers", "query_text").decode("utf-8")
        self.__searchbar.set_text(text)
        if Query.is_parsable(text):
            self.__filter_changed(self.__searchbar, text, restore=True)

    def __get_filter(self):
        return self.__filter or Query("")

    def can_filter_text(self):
        return True

    def filter_text(self, text):
        self.__searchbar.set_text(text)
        if Query.is_parsable(text):
            self.__filter_changed(self.__searchbar, text)
            self.activate()
        else:
            print_w("Not parseable: %s" % text)

    def get_filter_text(self):
        return self.__searchbar.get_text()

    def activate(self):
        print_d("Refreshing browser for query \"%r\"" % self.__filter)
        songs = self.library.query_with_refresh(self.get_filter_text())
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
        text = self.__searchbar.get_text().encode("utf-8")
        config.set("browsers", "query_text", text)
        self.api_client.save_token()

    def __handle_incoming_uri(self, obj, uri):
        uri = URI(uri)
        if uri.scheme == "quodlibet" and "/callbacks/soundcloud" in uri:
            try:
                code = parse_qs(uri.query)["code"][0]
            except IndexError:
                print_w("Malformed response in callback URI: %s" % uri)
                return
            print_d("Processing Soundcloud callback (%s)" % (uri,))
            self.api_client.get_token(code)
        else:
            print_w("Unknown scheme passed in URL (%s)" % (uri,))

    def __on_authenticated(self, obj, data):
        name = data.username
        msg = Message(Gtk.MessageType.INFO, app.window, _("Connected"),
                      _("Quod Libet is now connected, <b>%s</b>!") % name)
        msg.run()
        self.update_connect_button(self.api_client.online)
