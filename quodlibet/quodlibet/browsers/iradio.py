# -*- coding: utf-8 -*-
# Copyright 2011 Joe Wreschnig, Christoph Reiter
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

from __future__ import with_statement

import os
import sys
import bz2
import urllib2
import urllib
import itertools

import gobject
import gtk

from quodlibet import const
from quodlibet import qltk
from quodlibet import util
from quodlibet import config

from quodlibet.browsers._base import Browser
from quodlibet.formats.remote import RemoteFile
from quodlibet.formats._audio import TAG_TO_SORT, MIGRATE, AudioFile
from quodlibet.library import SongLibrary
from quodlibet.parse import Query
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.notif import Task
from quodlibet.util import copool, gobject_weak, sanitize_tags
from quodlibet.util.uri import URI
from quodlibet.qltk.views import AllTreeView
from quodlibet.qltk.searchbar import SearchBarBox
from quodlibet.qltk.completion import LibraryTagCompletion
from quodlibet.qltk.x import MenuItem, Alignment, ScrolledWindow
from quodlibet.qltk.menubutton import MenuButton

STATION_LIST_URL = "http://quodlibet.googlecode.com/files/radiolist.bz2"
STATIONS_FAV = os.path.join(const.USERDIR, "stations")
STATIONS_ALL = os.path.join(const.USERDIR, "stations_all")

# TODO: - Do the update in a thread
#       - Ranking: reduce duplicate stations (max 3 URLs per station)
#                  prefer stations that match a genre?

# Migration path for pickle
sys.modules["browsers.iradio"] = sys.modules[__name__]

class IRFile(RemoteFile):
    multisong = True
    can_add = False

    format = "Radio Station"

    __CAN_CHANGE = "title artist grouping".split()

    def __call__(self, key, *args, **kwargs):
        base_call = super(IRFile, self).__call__
        if key == "title" and "title" not in self and "organization" in self:
            return base_call("organization", *args, **kwargs)

        # split title by " - " if no artist tag is present and
        # this is not the main song: common format for shoutcast stations
        if not self.multisong and key in ("title", "artist") and \
                "title" in self and "artist" not in self:
            title = base_call("title").split(" - ", 1)
            if len(title) > 1:
                return (key == "title" and title[-1]) or title[0]

        if key == "~format" and "audio-codec" in self:
            return "%s (%s)" % (self.format,
                base_call("audio-codec", *args, **kwargs))
        return base_call(key, *args, **kwargs)

    def get(self, key, *args):
        base_call = super(IRFile, self).get
        if key in ("artist", TAG_TO_SORT["artist"]) and \
            not base_call(key, *args) and "website" in self:
            return base_call("website", *args)
        return base_call(key, *args)

    def write(self):
        pass

    def can_change(self, k=None):
        if k is None:
            return self.__CAN_CHANGE
        else:
            return k in self.__CAN_CHANGE


def ParsePLS(file):
    data = {}

    lines = file.readlines()
    if not lines or "[playlist]" not in lines.pop(0): return []

    for line in lines:
        try: head, val = line.strip().split("=", 1)
        except (TypeError, ValueError): continue
        else:
            head = head.lower()
            if head.startswith("length") and val == "-1": continue
            else: data[head] = val.decode('utf-8', 'replace')

    count = 1
    files = []
    warnings = []
    while True:
        if "file%d" % count in data:
            filename = data["file%d" % count].encode('utf-8', 'replace')
            if filename.lower()[-4:] in [".pls", ".m3u"]:
                warnings.append(filename)
            else:
                irf = IRFile(filename)
                for key in ["title", "genre", "artist"]:
                    try: irf[key] = data["%s%d" % (key, count)]
                    except KeyError: pass
                try: irf["~#length"] = int(data["length%d" % count])
                except (KeyError, TypeError, ValueError): pass
                files.append(irf)
        else: break
        count += 1

    if warnings:
        qltk.WarningMessage(
            None, _("Unsupported file type"),
            _("Station lists can only contain locations of stations, "
              "not other station lists or playlists. The following locations "
              "cannot be loaded:\n%s") % "\n  ".join(map(util.escape, warnings))
            ).run()

    return files


def ParseM3U(fileobj):
    files = []
    pending_title = None
    for line in fileobj:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            try: pending_title = line.split(",", 1)[1]
            except IndexError: pending_title = None
        elif line.startswith("http"):
            irf = IRFile(line)
            if pending_title:
                irf["title"] = pending_title.decode('utf-8', 'replace')
                pending_title = None
            files.append(irf)
    return files


def add_station(uri):
    """Fetches the URI content and extracts IRFiles"""

    irfs = []
    if isinstance(uri, unicode):
        uri = uri.encode('utf-8')

    if uri.lower().endswith(".pls") or uri.lower().endswith(".m3u"):
        try: sock = urllib.urlopen(uri)
        except EnvironmentError, e:
            try: err = e.strerror.decode(const.ENCODING, 'replace')
            except (TypeError, AttributeError):
                err = e.strerror[1].decode(const.ENCODING, 'replace')
            qltk.ErrorMessage(None, _("Unable to add station"), err).run()
            return []

        if uri.lower().endswith(".pls"):
            irfs = ParsePLS(sock)
        elif uri.lower().endswith(".m3u"):
            irfs = ParseM3U(sock)

        sock.close()
    else:
        try:
            irfs = [IRFile(uri)]
        except ValueError, err:
            qltk.ErrorMessage(None, _("Unable to add station"), err).run()

    return irfs


def download_taglist(callback, cofuncid, step=1024 * 10):
    """Generator for loading the bz2 compressed tag list.

    Calls callback with the decompressed data or None in case of
    an error."""

    with Task(_("Internet Radio"), _("Downloading station list")) as task:
        if cofuncid: task.copool(cofuncid)

        try:
            response = urllib2.urlopen(STATION_LIST_URL)
        except urllib2.URLError:
            gobject.idle_add(callback, None)
            return

        try:
            size = int(response.info().get("content-length", 0))
        except ValueError:
            size = 0

        decomp = bz2.BZ2Decompressor()

        data = ""
        temp = ""
        read = 0
        while temp or not data:
            read += len(temp)

            if size: task.update(float(read) / size)
            else: task.pulse()
            yield True

            try:
                data += decomp.decompress(temp)
                temp = response.read(step)
            except (IOError, EOFError):
                data = None
                break
        response.close()

        yield True

        stations = None
        if data:
            stations = parse_taglist(data)

        gobject.idle_add(callback, stations)


def parse_taglist(data):
    """Parses a dump file like list of tags and returns a list of IRFiles

    uri=http://...
    tag=value1
    tag2=value
    tag=value2
    uri=http://...
    ...

    """

    stations = []
    station = None

    for l in data.split("\n"):
        key = l.split("=")[0]
        value = l.split("=", 1)[1]
        if key == "uri":
            if station:
                stations.append(station)
            station = IRFile(value)
            continue

        value = util.decode(value)
        san = sanitize_tags({key: value}, stream=True).items()
        if not san:
            continue

        key, value = san[0]
        if isinstance(value, str):
            value = value.decode("utf-8")
            if value not in station.list(key):
                station.add(key, value)
        else:
            station[key] = value

    if station:
        stations.append(station)

    return stations


def sort_stations(station):
    bitrate = station("~#bitrate", 96)
    listeners = int(station("~listenerpeak", 20))
    return (listeners >= 20, bitrate, listeners)


class AddNewStation(GetStringDialog):
    def __init__(self, parent):
        super(AddNewStation, self).__init__(
            parent, _("New Station"),
            _("Enter the location of an Internet radio station:"),
            okbutton=gtk.STOCK_ADD)

    def _verify_clipboard(self, text):
        # try to extract an URI from the clipboard
        for line in text.splitlines():
            line = line.strip()

            try:
                URI(line)
            except ValueError:
                pass
            else:
                return line


class GenreFilter(object):
    STAR = ["genre", "organization"]

    # This probably needs improvements
    GENRES = {
        "electronic": (_("Electronic"),
            "|(electr,house,techno,trance,/trip.?hop/,&(drum,n,bass),chill,"
            "dnb,minimal,/down(beat|tempo)/,&(dub,step))"),
        "rap": (_("Hip Hop / Rap"), "|(&(hip,hop),rap)"),
        "oldies": (_("Oldies"), "|(/[2-9]0\S?s/,oldies)"),
        "r&b": (_("R&B"), "/r(\&|n)b/"),
        "japanese": (_("Japanese"), "|(anime,jpop,japan,jrock)"),
        "indian": (_("Indian"), "|(bollywood,hindi,indian,bhangra)"),
        "religious": (_("Religious"),
            "|(religious,christian,bible,gospel,spiritual,islam)"),
        "charts": (_("Charts"), "|(charts,hits,top)"),
        "turkish": (_("Turkish"), "|(turkish,turkce)"),
        "reggae": (_("Reggae / Dancehall"), "|(/reggae([^\w]|$)/,dancehall)"),
        "latin": (_("Latin"), "|(latin,salsa)"),
        "college": (_("College Radio"), "|(college,campus)"),
        "talk_news": (_("Talk / News"), "|(news,talk)"),
        "ambient": (_("Ambient"), "|(ambient,easy)"),
        "jazz": (_("Jazz"), "|(jazz,swing)"),
        "classical": (_("Classical"), "classic"),
        "pop": (_("Pop"), None),
        "alternative": (_("Alternative"), None),
        "metal": (_("Metal"), None),
        "country": (_("Country"), None),
        "news": (_("News"), None),
        "schlager": (_("Schlager"), None),
        "funk": (_("Funk"), None),
        "indie": (_("Indie"), None),
        "blues": (_("Blues"), None),
        "soul": (_("Soul"), None),
        "lounge": (_("Lounge"), None),
        "punk": (_("Punk"), None),
        "reggaeton": (_("Reggaeton"), None),
        "slavic": (_("Slavic"),
            "|(narodna,albanian,manele,shqip,kosova)"),
        "greek": (_("Greek"), None),
        "gothic": (_("Gothic"), None),
        "rock": (_("Rock"), None),
    }

    # parsing all above takes 350ms on an atom, so only generate when needed
    __CACHE = {}

    def keys(self):
        return self.GENRES.keys()

    def query(self, key):
        if key not in self.__CACHE:
            text, filter_ = self.GENRES[key]
            if filter_ is None:
                filter_ = key
            self.__CACHE[key] = Query(filter_, star=self.STAR)
        return self.__CACHE[key]

    def text(self, key):
        return self.GENRES[key][0]


class InternetRadio(gtk.VBox, Browser, util.InstanceTracker):
    __gsignals__ = Browser.__gsignals__

    __stations = None
    __fav_stations = None
    __librarian = None

    __filter = None

    name = _("Internet Radio")
    accelerated_name = _("_Internet Radio")
    priority = 16
    headers = "title artist ~people grouping genre website ~format " \
        "channel-mode ~listenerpeak".split()

    TYPE, STOCK, KEY, NAME = range(4)
    TYPE_FILTER, TYPE_ALL, TYPE_FAV, TYPE_SEP, TYPE_NOCAT = range(5)
    STAR = ["artist", "title", "website", "genre", "comment"]

    @classmethod
    def _init(klass, library):
        klass.__librarian = library.librarian

        klass.__stations = SongLibrary("iradio-remote")
        klass.__stations.load(STATIONS_ALL, skip=lambda x: True)

        klass.__fav_stations = SongLibrary("iradio")
        klass.__fav_stations.load(STATIONS_FAV, skip=lambda x: True)

        klass.filters = GenreFilter()

    @classmethod
    def _destroy(klass):
        if klass.__stations.dirty:
            klass.__stations.save()
        klass.__stations.destroy()
        klass.__stations = None

        if klass.__fav_stations.dirty:
            klass.__fav_stations.save()
        klass.__fav_stations.destroy()
        klass.__fav_stations = None

        klass.__librarian = None

        klass.filters = None

    def __inhibit(self):
        self.view.get_selection().handler_block(self.__changed_sig)

    def __uninhibit(self):
        self.view.get_selection().handler_unblock(self.__changed_sig)

    def __destroy(self, *args):
        if not self.instances():
            self._destroy()

    def __init__(self, library, main):
        super(InternetRadio, self).__init__(spacing=12)

        if not self.instances():
            self._init(library)
        self._register_instance()

        self.connect('destroy', self.__destroy)

        completion = LibraryTagCompletion(self.__stations)
        self.accelerators = gtk.AccelGroup()
        self.__searchbar = search = SearchBarBox(completion=completion,
                                                 accel_group=self.accelerators)
        gobject_weak(search.connect, 'query-changed', self.__filter_changed)

        menu = gtk.Menu()
        new_item = MenuItem(_("_New Station"), gtk.STOCK_ADD)
        gobject_weak(new_item.connect, 'activate', self.__add)
        menu.append(new_item)
        update_item = MenuItem(_("_Update Stations"), gtk.STOCK_REFRESH)
        gobject_weak(update_item.connect, 'activate', self.__update)
        menu.append(update_item)
        menu.show_all()

        button = MenuButton(
            gtk.image_new_from_stock(
                gtk.STOCK_PREFERENCES, gtk.ICON_SIZE_MENU),
                arrow=True)
        button.set_menu(menu)

        def focus(widget, *args):
            qltk.get_top_parent(widget).songlist.grab_focus()
        gobject_weak(search.connect, 'focus-out', focus, parent=self)

        # treeview
        scrolled_window = ScrolledWindow()
        scrolled_window.set_shadow_type(gtk.SHADOW_IN)
        self.view = view = AllTreeView()
        view.set_headers_visible(False)
        scrolled_window.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        scrolled_window.add(view)
        model = gtk.ListStore(int, str, str, str)

        model.append(row=[self.TYPE_ALL, gtk.STOCK_DIRECTORY, "__all",
                          _("All Stations")])
        model.append(row=[self.TYPE_SEP, gtk.STOCK_DIRECTORY, "", ""])
        #Translators: Favorite radio stations
        model.append(row=[self.TYPE_FAV, gtk.STOCK_DIRECTORY, "__fav",
                          _("Favorites")])
        model.append(row=[self.TYPE_SEP, gtk.STOCK_DIRECTORY, "", ""])

        filters = self.filters
        for text, k in sorted([(filters.text(k), k) for k in filters.keys()]):
            model.append(row=[self.TYPE_FILTER, gtk.STOCK_FIND, k, text])

        model.append(row=[self.TYPE_NOCAT, gtk.STOCK_DIRECTORY,
                          "nocat", _("No Category")])

        def separator(model, iter):
            return model[iter][self.TYPE] == self.TYPE_SEP
        view.set_row_separator_func(separator)

        def search_func(model, column, key, iter):
            return key.lower() not in model[iter][column].lower()
        view.set_search_column(self.NAME)
        view.set_search_equal_func(search_func)

        column = gtk.TreeViewColumn("genres")
        column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)

        renderpb = gtk.CellRendererPixbuf()
        renderpb.props.xpad = 3
        column.pack_start(renderpb, False)
        column.set_attributes(renderpb, stock_id=self.STOCK)

        render = gtk.CellRendererText()
        view.append_column(column)
        column.pack_start(render)
        column.set_attributes(render, text=self.NAME)

        view.set_model(model)

        # selection
        selection = view.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.__changed_sig = gobject_weak(selection.connect, 'changed',
            util.DeferredSignal(lambda x: self.activate()), parent=view)

        box = gtk.HBox(spacing=6)
        box.pack_start(search)
        box.pack_start(button, expand=False)
        if main:
            self.pack_start(Alignment(box, left=3, right=3, top=3))
        else:
            self.pack_start(box)
        self.__filter_list = scrolled_window

        self.show_all()

    def pack(self, songpane):
        container = gtk.VBox(spacing=6)
        pane = qltk.RHPaned()
        pane.pack1(self.__filter_list, resize=False, shrink=False)
        pane.show_all()
        pane.pack2(songpane, resize=True, shrink=False)
        container.pack_start(self, expand=False)
        container.pack_start(pane)
        return container

    def unpack(self, container, songpane):
        container.remove(self)
        pane = container.get_children()[0]
        pane.remove(songpane)

    def __update(self, *args):
        copool.add(download_taglist, self.__update_done,
                   cofuncid="radio-load", funcid="radio-load")

    def __update_done(self, stations):
        if not stations:
            print_w("Loading remote station list failed.")
            return

        # take the best 4000
        stations.sort(key=sort_stations, reverse=True)
        stations = stations[:4000]

        # remove the tags only used for ranking
        for s in stations:
            s.pop("~listenerpeak", None)

        stations = dict(((s.key, s) for s in stations))

        # don't add ones that are in the fav list
        for fav in self.__fav_stations.iterkeys():
            stations.pop(fav, None)

        # separate
        o, n = set(self.__stations.iterkeys()), set(stations)
        to_add, to_change, to_remove = n - o, o & n, o - n
        del o, n

        # migrate stats
        to_change = [stations.pop(k) for k in to_change]
        for new in to_change:
            old = self.__stations[new.key]
            # clear everything except stats
            AudioFile.reload(old)
            # add new metadata except stats
            for k in (x for x in new.iterkeys() if x not in MIGRATE):
                old[k] = new[k]

        to_add = [stations.pop(k) for k in to_add]
        to_remove = [self.__stations[k] for k in to_remove]

        self.__stations.remove(to_remove)
        self.__stations.changed(to_change)
        self.__stations.add(to_add)

    def __filter_changed(self, bar, text, restore=False):
        self.__filter = None
        if not Query.match_all(text):
            self.__filter = Query(text, self.STAR)

        if not restore:
            self.activate()

    def __get_selected_libraries(self):
        """Returns the libraries to search in depending on the
        filter selection"""

        selection = self.view.get_selection()
        model, rows = selection.get_selected_rows()
        types = [model[row][self.TYPE] for row in rows]
        libs = [self.__fav_stations]
        if types != [self.TYPE_FAV]:
            libs.append(self.__stations)

        return libs

    def __get_selection_filter(self):
        """Retuns a filter object for the current selection or None
        if nothing should be filtered"""

        selection = self.view.get_selection()
        model, rows = selection.get_selected_rows()

        filter_ = None
        for row in rows:
            type_ = model[row][self.TYPE]
            if type_ == self.TYPE_FILTER:
                key = model[row][self.KEY]
                current_filter = self.filters.query(key)
                if current_filter:
                    if filter_:
                        filter_ |= current_filter
                    else:
                        filter_ = current_filter
            elif type_ == self.TYPE_NOCAT:
                # if notcat is selected, combine all filters, negate and merge
                all_ = [self.filters.query(k) for k in self.filters.keys()]
                nocat_filter = all_ and -reduce(lambda x, y: x | y, all_)
                if nocat_filter:
                    if filter_:
                        filter_ |= nocat_filter
                    else:
                        filter_ = nocat_filter
            elif type_ == self.TYPE_ALL:
                filter_ = None
                break

        return filter_

    def __add_fav(self, songs):
        songs = [s for s in songs if s in self.__stations]
        type(self).__librarian.move(
            songs, self.__stations, self.__fav_stations)

    def __remove_fav(self, songs):
        songs = [s for s in songs if s in self.__fav_stations]
        type(self).__librarian.move(
            songs, self.__fav_stations, self.__stations)

    def __add(self, button):
        parent = qltk.get_top_parent(self)
        uri = (AddNewStation(parent).run(clipboard=True) or "").strip()
        if uri != "":
            self.__add_station(uri)

    def __add_station(self, uri):
        irfs = add_station(uri)

        if not irfs:
            qltk.ErrorMessage(
                None, _("No stations found"),
                _("No Internet radio stations were found at %s.") %
                util.escape(uri)).run()
            return

        irfs = filter(lambda station: station not in self.__fav_stations, irfs)
        if not irfs:
            qltk.WarningMessage(
                None, _("Unable to add station"),
                _("All stations listed are already in your library.")).run()

        if irfs:
            self.__fav_stations.add(irfs)

    def Menu(self, songs, songlist, library):
        menu = SongsMenu(self.__librarian, songs, playlists=False, remove=True,
                         queue=False, accels=songlist.accelerators,
                         devices=False, parent=self)

        menu.prepend(gtk.SeparatorMenuItem())

        in_fav = False
        in_all = False
        for song in songs:
            if song in self.__fav_stations:
                in_fav = True
            elif song in self.__stations:
                in_all = True
            if in_fav and in_all:
                break

        button = MenuItem(_("Remove from Favorites"), gtk.STOCK_REMOVE)
        button.set_sensitive(in_fav)
        gobject_weak(button.connect_object, 'activate',
                     self.__remove_fav, songs)
        menu.prepend(button)

        button = MenuItem(_("Add to Favorites"), gtk.STOCK_ADD)
        button.set_sensitive(in_all)
        gobject_weak(button.connect_object, 'activate',
                     self.__add_fav, songs)
        menu.prepend(button)

        return menu

    def restore(self):
        text = config.get("browsers", "query_text").decode("utf-8")
        self.__searchbar.set_text(text)
        if Query.is_parsable(text):
            self.__filter_changed(self.__searchbar, text, restore=True)

        keys = config.get("browsers", "radio").splitlines()
        def select_func(row):
            return row[self.TYPE] != self.TYPE_SEP and row[self.KEY] in keys

        self.__inhibit()
        view = self.view
        if not view.select_by_func(select_func):
            for row in view.get_model():
                if row[self.TYPE] == self.TYPE_FAV:
                    view.set_cursor(row.path)
                    break
        self.__uninhibit()

    def __get_filter(self):
        filter_ = self.__get_selection_filter()

        if filter_:
            if self.__filter:
                filter_ &= self.__filter
        else:
            filter_ = self.__filter

        return filter_

    def activate(self):
        filter_ = self.__get_filter()
        libs = self.__get_selected_libraries()
        songs = itertools.chain(*libs)

        if filter_:
            songs = filter(filter_.search, songs)
        else:
            songs = list(songs)

        self.emit('songs-selected', songs, None)

    def active_filter(self, song):
        for lib in self.__get_selected_libraries():
            if song in lib:
                break
        else:
            return False

        filter_ = self.__get_filter()

        if filter_:
            return filter_.search(song)
        return True

    def save(self):
        text = self.__searchbar.get_text().encode("utf-8")
        config.set("browsers", "query_text", text)

        selection = self.view.get_selection()
        model, rows = selection.get_selected_rows()
        names = filter(None, [model[row][self.KEY] for row in rows])
        config.set("browsers", "radio", "\n".join(names))

    def scroll(self, song):
        # nothing we care about
        if song not in self.__stations and song not in self.__fav_stations:
            return

        path = None
        for row in self.view.get_model():
            if row[self.TYPE] == self.TYPE_FILTER:
                if self.filters.query(row[self.KEY]).search(song):
                    path = row.path
                    break
        else:
            # in case nothing matches, select all
            path = (0,)

        self.view.scroll_to_cell(path, use_align=True, row_align=0.5)
        self.view.set_cursor(path)

    def statusbar(self, i):
        return ngettext("%(count)d station", "%(count)d stations", i)


from quodlibet import player
if player.can_play_uri("http://"):
    browsers = [InternetRadio]
else: browsers = []
