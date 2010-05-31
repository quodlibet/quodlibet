# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation

import os
import urllib
import re
from xml.parsers import expat

import gobject
import gtk
import pango

from quodlibet import const
from quodlibet import qltk
from quodlibet import util

from quodlibet.browsers._base import Browser
from quodlibet.formats.remote import RemoteFile
from quodlibet.library import SongLibrary
from quodlibet.parse import Query
from quodlibet.qltk.entry import ValidatingEntry
from quodlibet.qltk.getstring import GetStringDialog
from quodlibet.qltk.songsmenu import SongsMenu
from quodlibet.qltk.views import HintedTreeView

ICECAST_YP = "http://dir.xiph.org/yp.xml"
STATIONS = os.path.join(const.USERDIR, "stations")

class IRFile(RemoteFile):
    multisong = True
    can_add = False

    format = "Radio Station"

    __CAN_CHANGE = "title artist grouping".split()

    def write(self): pass
    def can_change(self, k=None):
        if k is None: return self.__CAN_CHANGE
        else: return k in self.__CAN_CHANGE

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
              "cannot be loaded:\n%s") % "\n  ".join(map(util.escape,warnings))
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

class YPParser(object):
    _valid_keys = "server_name listen_url server_type bitrate genre"
    def __init__(self):
        self.parser = expat.ParserCreate()
        self.parser.StartElementHandler = self.handle_start
        self.parser.EndElementHandler = self.handle_end
        self.parser.CharacterDataHandler = self.handle_char_data
    def handle_start(self, name, attrs):
        if name in self._valid_keys:
            self._key = name
            self._val = ''
        if name == 'entry':
            self._current = {}
    def handle_char_data(self, data):
        if self._key:
            self._val = self._val + data
    def handle_end(self, name):
        if name == 'entry':
            type = self._current.get("server_type")
            if type.startswith("audio") or (type == "application/ogg" and
                not self._current.get("listen_url").endswith("ogv")):
                irf = IRFile(self._current.get("listen_url"))
                irf["title"] = self._current.get("server_name", u"")
                genres = self._current.get("genre", u"").split()
                irf["genre"] = '\n'.join(filter(lambda s: len(s) > 1, genres))
                try: br = int(self._current.get("bitrate", 0))
                except: br = 0
                if br > 1000: br = br / 1000
                irf["~#bitrate"] = br
                self.files.append(irf)
            self._current = None
        elif self._key and self._current is not None:
            self._current[self._key] = self._val.strip()
            self._key = None
            self._val = None
    def parse(self, fileobj):
        self.files = []
        self._key = None
        self.parser.ParseFile(fileobj)
        return self.files

class ChooseNewStations(gtk.Dialog):
    def __init__(self, irfs):
        super(ChooseNewStations, self).__init__(title=_("Choose New Stations"))
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_ADD, gtk.RESPONSE_OK)
        self.set_default_size(500, 400)
        has_genre, has_bitrate = (False, False)
        for song in irfs:
            if song("genre"): has_genre = True
            if song("~#bitrate"): has_bitrate = True

        # (song, index, visible, checked, title, genres, bitrate)
        listmodel = gtk.ListStore(object, int, bool, bool, str, str, int)
        filtermodel = listmodel.filter_new()
        filtermodel.set_visible_column(2)
        model = gtk.TreeModelSort(filtermodel)
        hbox_search = gtk.HBox()
        lbl = gtk.Label(_('_Search:'))
        lbl.set_use_underline(True)
        hbox_search.pack_start(lbl, expand=False)
        query = gtk.Entry()
        lbl.set_mnemonic_widget(query)
        def filter_visible(query, filter, listmodel):
            iter = listmodel.get_iter_root()
            qre_text = '|'.join(re.escape(query.get_text()).split())
            query_re = re.compile(qre_text, flags = re.IGNORECASE)
            while iter:
                (title, genres) = listmodel.get(iter, 4, 5)
                if query_re.search(title) or query_re.search(genres):
                    listmodel.set_value(iter, 2, True)
                else:
                    listmodel.set_value(iter, 2, False)
                iter = listmodel.iter_next(iter)
            filter.refilter()
        query.connect('changed', filter_visible, filtermodel, listmodel)
        hbox_search.pack_start(query)
        self.vbox.pack_start(hbox_search, expand=False)

        self.tv = tv = HintedTreeView()
        tv.set_model(model)
        render = gtk.CellRendererToggle()
        render.connect('toggled', self.__toggled)
        c = gtk.TreeViewColumn(_("Add"), render, active=3)
        tv.append_column(c)
        # These next two are out of model order so that resizing works better
        if has_bitrate:
            render = gtk.CellRendererText()
            render.set_property('xalign', 1.0)
            c = gtk.TreeViewColumn(_("Bitrate"), render, text=6)
            c.set_sort_column_id(6)
            tv.append_column(c)
        if has_genre:
            render = gtk.CellRendererText()
            render.set_property('ellipsize', pango.ELLIPSIZE_END)
            render.set_property('width', 100)
            c = gtk.TreeViewColumn(_("Genre"), render, text=5)
            c.set_property('resizable', True)
            c.set_sort_column_id(5)
            tv.append_column(c)
        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        c = gtk.TreeViewColumn(_("Title"), render, text=4)
        c.set_property('resizable', True)
        c.set_sort_column_id(4)
        tv.append_column(c)
        tv.set_search_column(4)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(tv)
        sw.set_border_width(6)
        self.vbox.pack_start(sw)

        for id, song in enumerate(irfs):
            listmodel.append([song, id, True, False, song("~artist~title"),
                              ', '.join(song("genre").split()),
                              song("~#bitrate", 0)])
        self.listmodel = listmodel
        self.model = model
        self.connect_object('destroy', tv.set_model, None)
        self.child.show_all()

    def __toggled(self, toggle, path):
        listmodel_path = self.model[path][1]
        self.listmodel[listmodel_path][3] ^= True

    def get_irfs(self):
        stations = [row[0] for row in self.model if row[2] and row[3]]
        if not stations:
            # If none are checked, try going with what's selected instead
            model, iter = self.tv.get_selection().get_selected()
            if iter:
                stations = [model[iter][0]]
        return stations

class AddNewStation(GetStringDialog):
    def __init__(self, parent):
        super(AddNewStation, self).__init__(
            parent, _("New Station"),
            _("Enter the location of an Internet radio station:"),
            okbutton=gtk.STOCK_ADD)
        b = qltk.Button(_("_Stations..."), gtk.STOCK_CONNECT)
        b.connect_object('clicked', self._val.set_text, ICECAST_YP)
        b.connect_object('clicked', self.response, gtk.RESPONSE_OK)
        b.show_all()
        self.action_area.pack_start(b, expand=False)
        self.action_area.reorder_child(b, 0)

class InternetRadio(gtk.HBox, Browser):
    __gsignals__ = Browser.__gsignals__
    __stations = SongLibrary("iradio")
    __sig = None
    __filter = None
    __refill_id = None

    headers = "title artist ~people grouping genre website".split()

    name = _("Internet Radio")
    accelerated_name = _("_Internet Radio")
    priority = 15

    @classmethod
    def init(klass, library):
        klass.__stations.load(STATIONS)

    def __init__(self, library, player):
        super(InternetRadio, self).__init__(spacing=12)
        self.commands = {"add-station": self.__add_station_remote}

        add = qltk.Button(_("_New Station"), gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        self.__search = gtk.Entry()
        self.pack_start(add, expand=False)
        add.connect('clicked', self.__add)
        if InternetRadio.__sig is None:
            InternetRadio.__sig = library.connect(
                'changed', InternetRadio.__changed)

        for s in [self.__stations.connect('removed', self.activate),
                  self.__stations.connect('added', self.activate)
                  ]:
            self.connect_object('destroy', self.__stations.disconnect, s)
        self.connect_object('destroy', self.__stations.save, STATIONS)
        self.connect_object('destroy', self.emit, 'songs-selected', [], None)

        hb = gtk.HBox(spacing=3)
        lab = gtk.Label(_("_Search:"))
        self.pygtkbug = search = ValidatingEntry(Query.is_valid_color)
        lab.set_use_underline(True)
        lab.set_mnemonic_widget(search)
        search.connect('changed', self.__filter_changed)
        hb.pack_start(lab, expand=False)
        hb.pack_start(search)
        search.pack_clear_button(hb)
        self.pack_start(hb)

        self.show_all()
        gobject.idle_add(self.activate)

    def __filter_changed(self, entry):
        if self.__refill_id is not None:
            gobject.source_remove(self.__refill_id)
            self.__refill_id = None
        text = entry.get_text().decode('utf-8')
        if Query.is_parsable(text):
            star = ["artist", "album", "title", "website", "genre", "comment"]
            if text: self.__filter = Query(text, star).search
            else: self.__filter = None
            self.__refill_id = gobject.timeout_add(500, self.activate)

    def Menu(self, songs, songlist, library):
        menu = SongsMenu(self.__stations, songs, playlists=False,
                         queue=False, accels=songlist.accelerators,
                         parent=self)
        return menu

    def __remove(self, button, songs):
        self.__stations.remove(songs)
        self.__stations.save(STATIONS)
        self.activate()

    def __changed(klass, library, songs):
        if filter(lambda s: s in klass.__stations, songs):
            klass.__stations.save(STATIONS)
    __changed = classmethod(__changed)

    def __add_station_remote(self, *args):
        gtk.threads_enter()
        if len(args) == 3:
            self.__add(None, args[0])
        else:
            self.__add_station(args[0], args[1])
        gtk.threads_leave()

    def __add(self, button):
        uri = (AddNewStation(qltk.get_top_parent(self)).run() or "").strip()
        if uri == "": return
        else: self.__add_station(uri)

    def __add_station(self, uri):
        if isinstance(uri, unicode): uri = uri.encode('utf-8')
        if uri.lower().endswith(".pls") or uri.lower().endswith(".m3u") \
            or uri == ICECAST_YP:
            try: sock = urllib.urlopen(uri)
            except EnvironmentError, e:
                try: err = e.strerror.decode(const.ENCODING, 'replace')
                except (TypeError, AttributeError):
                    err = e.strerror[1].decode(const.ENCODING, 'replace')
                qltk.ErrorMessage(None, _("Unable to add station"), err).run()
                return
            if uri.lower().endswith(".pls"):
                irfs = ParsePLS(sock)
            elif uri.lower().endswith(".m3u"):
                irfs = ParseM3U(sock)
            elif uri == ICECAST_YP:
                p = YPParser()
                irfs = p.parse(sock)
            sock.close()
        else:
            try:
                irfs = [IRFile(uri)]
            except ValueError, err:
                qltk.ErrorMessage(None, _("Unable to add station"), err).run()
                return

        if not irfs:
            qltk.ErrorMessage(
                None, _("No stations found"),
                _("No Internet radio stations were found at %s.") %
                util.escape(uri)).run()
            return

        irfs = filter(lambda station: station not in self.__stations, irfs)
        if not irfs:
            qltk.WarningMessage(
                None, _("Unable to add station"),
                _("All stations listed are already in your library.")).run()
        elif len(irfs) > 1:
            d = ChooseNewStations(sorted(irfs))
            if d.run() == gtk.RESPONSE_OK:
                irfs = d.get_irfs()
            else:
                irfs = []
            d.destroy()
        if irfs and self.__stations.add(irfs):
            self.__stations.save(STATIONS)

    def restore(self): self.activate()
    def activate(self, *args):
        self.emit('songs-selected',
                  filter(self.__filter, self.__stations), None)

    def save(self): pass

    def statusbar(self, i):
        return ngettext("%(count)d station", "%(count)d stations", i)

from quodlibet import player
if player.can_play_uri("http://"):
    browsers = [InternetRadio]
else: browsers = []
