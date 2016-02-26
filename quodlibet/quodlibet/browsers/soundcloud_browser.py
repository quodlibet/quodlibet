# -*- coding: utf-8 -*-
# Copyright 2016 Nick Boultbee
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from datetime import datetime
from gi.repository import Gtk, Pango, GLib
from urlparse import parse_qs

from quodlibet.plugins import MissingModulePluginException

try:
    import soundcloud as sc
except ImportError:
    raise MissingModulePluginException("soundcloud")

from quodlibet import config, print_d, print_w
from quodlibet import qltk
from quodlibet import util
from quodlibet.browsers import Browser
from quodlibet.formats.remote import RemoteFile
from quodlibet.library import SongLibrary
from quodlibet.qltk import Icons, Message
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.menubutton import MenuButton
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.x import Align, ScrolledWindow
from quodlibet.qltk.x import SymbolicIconImage
from quodlibet.query import Query
from quodlibet.util import connect_destroy, website, DeferredSignal
from quodlibet.util.uri import URI

DEFAULT_BITRATE = 128
EPOCH = datetime(1970, 1, 1)


class SoundcloudApiClient(object):
    __CLIENT_SECRET = 'ca2b69301bd1f73985a9b47224a2a239'
    __CLIENT_ID = '5acc74891941cfc73ec8ee2504be6617'

    def __init__(self, token=None):
        super(SoundcloudApiClient, self).__init__()
        self.online = False
        self.access_token = token
        print_d("Starting Soundcloud API...")
        # create client object with app credentials
        if self.access_token:
            print_d("Using saved Soundcloud token...")
            self._setup()
        else:
            self.client = sc.Client(
                client_id=self.__CLIENT_ID,
                client_secret=self.__CLIENT_SECRET,
                redirect_uri='quodlibet://soundcloud/callback')
            # redirect user to authorize URL
            website(self.client.authorize_url() + "&display=popup")

    def get_token(self, code):
        client = self.client
        print_d("Getting access token...")
        result = client.exchange_token(code)
        print_d("Got an access token: %s" % result.access_token)
        self.access_token = result.access_token
        self._setup()

    def _setup(self):
        self.client = self._new_client(self.access_token)
        if self.client:
            self.save_token()

    @classmethod
    def _new_client(cls, token):
        try:
            return sc.Client(client_id=cls.__CLIENT_ID,
                             client_secret=cls.__CLIENT_SECRET,
                             access_token=token)
        except Exception as e:
            print_w("Couldn't authenticate (%r)" % e)
            return None

    @util.cached_property
    def username(self):
        return self.client.get('/me').username

    @property
    def username(self):
        return self.client.get('/me').username

    def get_tracks(self, query):
        params = {
            "q": query,
            "limit": 50,
            "duration[from]": 100 * 1000,
            "duration[to]": 10000 * 1000
        }
        print_d("Getting tracks: params=%s" % params)
        return self.client.get('/tracks', **params)

    @classmethod
    def add_secret(cls, stream_url):
        return "%s?client_id=%s" % (stream_url, cls.__CLIENT_ID)

    def save_token(self):
        if self.access_token:
            config.set("browsers", "soundcloud_token", self.access_token)


class SoundcloudLibrary(SongLibrary):
    STAR = ["artist", "title", "genre", "comment"]

    def __init__(self, client):
        super(SoundcloudLibrary, self).__init__("Soundcloud")
        self.client = client

    def audiofile_for(cls, response):
        r = response
        d = r.obj
        dl = d.get("downloadable", False) and d.get("download_url", None)
        uri = SoundcloudApiClient.add_secret(dl or r.stream_url)
        song = RemoteFile(uri=uri)
        print_d("Parsing %s" % r.obj)

        def get_utc_date(s):
            parts = s.split()
            dt = datetime.strptime(" ".join(parts[:-1]), "%Y/%m/%d %H:%M:%S")
            return int((dt - EPOCH).total_seconds())

        def put_time(tag, r, attr):
            try:
                song[tag] = get_utc_date(r.get(attr))
            except AttributeError:
                pass

        def put_date(tag, r, attr):
            try:
                parts = r.obj.get(attr).split()
                dt = datetime.strptime(" ".join(parts[:-1]),
                                       "%Y/%m/%d %H:%M:%S")
                song[tag] = dt.strftime("%Y-%m-%d")
            except AttributeError:
                pass

        def put_counts(*args):
            for name in args:
                tag = "%s_count" % name
                try:
                    song["~#%s" % tag] = int(r.obj.get(tag))
                except AttributeError:
                    pass

        try:
            song.update(title=r.title,
                        artist=r.user["username"],
                        comment=r.description,
                        website=r.permalink_url,
                        genre="\n".join(r.genre and r.genre.split(",") or []))
            if dl:
                song.update(format=r.original_format)
                song["~#bitrate"] = r.original_content_size * 8 / r.duration
            else:
                song["~#bitrate"] = DEFAULT_BITRATE
            song["~#length"] = int(r.duration) / 1000
            song["soundcloud_track_id"] = r.id
            art_url = r.artwork_url
            if art_url:
                song["artwork_url"] = (
                    art_url.replace("-large.", "-t500x500."))
            put_time("~#mtime", r, "last_modified")
            put_date("date", r, "created_at")
            if d.get("user_favorite", False):
                song["~#rating"] = 1.0
            put_counts("playback", "download", "favoritings", "likes")
            plays = d.get("user_playback_count", 0)
            if plays:
                song["~#playcount"] = plays
            print_d("Got song: %s" % song)
        except Exception as e:
            print_w("Couldn't parse a song from %s (%r). "
                    "Had these tags:\n  %s" % (r, e, song.keys()))
        return song

    def query(self, text, sort=None, star=STAR):
        return Query(text).filter(self._contents.values())

    def query_with_refresh(self, text, sort=None, star=STAR):
        """Queries Soundcloud for some (more) relevant results, then filters"""
        # TODO: a much better way of doing this

        def update():
            print_d("Updating library with new results...")
            new = self.get_tracks(text.strip('"\''))
            self.add(new)

        GLib.idle_add(update)

        return self.query(text, sort, star)

    def get_tracks(self, text):
        result = self.client.get_tracks(text)
        try:
            return [self.audiofile_for(r) for r in result]
        except AttributeError as e:
            print_w("Couldn't parse results (%s). Try %s"
                    % (e, result[0].keys()))
            return []


class SoundcloudBrowser(Browser, util.InstanceTracker):

    background = False
    __librarian = None
    __filter = None

    name = _("Soundcloud Browser")
    accelerated_name = _("Sound_cloud")
    keys = ["Soundcloud"]
    priority = 30
    uses_main_library = False
    headers = ("artist title ~#length genre ~mtime ~bitrate date website "
               "comment ~rating ~#playback_count ~#likes_count").split()

    TYPE, ICON_NAME, KEY, NAME = range(4)
    TYPE_FILTER, TYPE_ALL, TYPE_SEP, TYPE_NOCAT = range(4)
    STAR = SoundcloudLibrary.STAR

    @classmethod
    def _init(klass, library):
        klass.__librarian = library.librarian
        klass.filters = {"All": Query("", star=klass.STAR)}
        token = config.get("browsers", "soundcloud_token", default=None)
        klass.api_client = SoundcloudApiClient(token)
        klass.library = SoundcloudLibrary(klass.api_client)

    @classmethod
    def _destroy(klass):
        klass.__librarian = None

        klass.filters = {}

    def __inhibit(self):
        self.view.get_selection().handler_block(self.__changed_sig)

    def __uninhibit(self):
        self.view.get_selection().handler_unblock(self.__changed_sig)

    def __destroy(self, *args):
        if not self.instances():
            self._destroy()

    def __handle_incoming_uri(self, obj, uri):
        uri = URI(uri)
        if uri.scheme == "quodlibet" and "/soundcloud/callback" in uri:
            try:
                code = parse_qs(uri.query)["code"][0]
            except IndexError:
                print_w("Malformed response in callback URI: %s" % uri)
                return
            print_d("Processing Soundcloud callback (%s)" % (uri,))
            self.api_client.get_token(code)
            name = self.api_client.username
            msg = Message(Gtk.MessageType.INFO, app.window, _("Connected"),
                          _("Welcome to Quod Libet, <b>%s</b>!") % name)
            msg.run()
        else:
            print_w("Unknown scheme passed in URL (%s)" % (uri,))

    def __init__(self, library):
        super(SoundcloudBrowser, self).__init__(spacing=12)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        if not self.instances():
            self._init(library)
        self._register_instance()

        self.connect('destroy', self.__destroy)
        self.connect('uri-received', self.__handle_incoming_uri)

        completion = LibraryTagCompletion(library)
        self.accelerators = Gtk.AccelGroup()
        self.__searchbar = search = SearchBarBox(completion=completion,
                                                 accel_group=self.accelerators)
        search.timeout = 3000
        search.connect('query-changed', self.__filter_changed)

        menu = Gtk.Menu()
        menu.show_all()

        button = MenuButton(
            SymbolicIconImage(Icons.EMBLEM_SYSTEM, Gtk.IconSize.MENU),
            arrow=True)
        button.set_menu(menu)

        def focus(widget, *args):
            qltk.get_top_parent(widget).songlist.grab_focus()
        search.connect('focus-out', focus)

        # treeview
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

        model.append(row=[self.TYPE_SEP, Icons.FOLDER, "", ""])

        filters = self.filters
        for name, query in sorted(filters.iteritems()):
            model.append(row=[self.TYPE_FILTER,
                              Icons.EDIT_FIND,
                              name,
                              name])

        model.append(row=[self.TYPE_NOCAT, Icons.FOLDER,
                          "nocat", _("No Category")])

        def separator(model, iter, data):
            return model[iter][self.TYPE] == self.TYPE_SEP
        view.set_row_separator_func(separator, None)

        def search_func(model, column, key, iter, data):
            return key.lower() not in model[iter][column].lower()
        view.set_search_column(self.NAME)
        view.set_search_equal_func(search_func, None)

        column = Gtk.TreeViewColumn("genres")
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)

        renderpb = Gtk.CellRendererPixbuf()
        renderpb.props.xpad = 3
        column.pack_start(renderpb, False)
        column.add_attribute(renderpb, "icon-name", self.ICON_NAME)

        render = Gtk.CellRendererText()
        render.set_property('ellipsize', Pango.EllipsizeMode.END)
        view.append_column(column)
        column.pack_start(render, True)
        column.add_attribute(render, "text", self.NAME)

        view.set_model(model)

        # selection
        selection = view.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.__changed_sig = connect_destroy(selection, 'changed',
                DeferredSignal(lambda x: self.activate()))

        box = Gtk.HBox(spacing=6)
        box.pack_start(search, True, True, 0)
        box.pack_start(button, False, True, 0)
        self._searchbox = Align(box, left=0, right=6, top=6)
        self._searchbox.show_all()

        pane = qltk.ConfigRHPaned("browsers", "soundcloud_pos", 0.4)
        pane.show()
        pane.pack1(scrolled_window, resize=False, shrink=False)
        songbox = Gtk.VBox(spacing=6)
        songbox.pack_start(self._searchbox, False, True, 0)
        self._songpane_container = Gtk.VBox()
        self._songpane_container.show()
        songbox.pack_start(self._songpane_container, True, True, 0)
        songbox.show()
        pane.pack2(songbox, resize=True, shrink=False)
        self.pack_start(pane, True, True, 0)
        self.show()

    def pack(self, songpane):
        container = Gtk.VBox()
        container.add(self)
        self._songpane_container.add(songpane)
        return container

    def unpack(self, container, songpane):
        self._songpane_container.remove(songpane)
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


from quodlibet import app
if not app.player or app.player.can_play_uri("http://"):
    browsers = [SoundcloudBrowser]
else:
    browsers = []
