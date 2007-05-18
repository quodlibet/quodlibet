# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import urllib

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

SACREDCHAO = ("http://www.sacredchao.net/quodlibet/wiki/QL/"
              "Master.qlpls?format=txt")
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

class ChooseNewStations(gtk.Dialog):
    def __init__(self, irfs):
        super(ChooseNewStations, self).__init__(title=_("Choose New Stations"))
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_ADD, gtk.RESPONSE_OK)
        self.set_default_size(400, 300)

        tv = gtk.TreeView()
        model = gtk.ListStore(object, bool, str)
        tv.set_model(model)
        render = gtk.CellRendererToggle()
        render.connect('toggled', self.__toggled)
        c = gtk.TreeViewColumn(_("Add"), render, active=1)
        tv.append_column(c)
        render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        c = gtk.TreeViewColumn(_("Title"), render, text=2)
        tv.append_column(c)

        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(tv)
        sw.set_border_width(6)

        self.vbox.pack_start(sw)

        for song in irfs:
            model.append([song, False, song("~artist~title")])
        self.model = model
        self.connect_object('destroy', tv.set_model, None)
        self.child.show_all()

    def __toggled(self, toggle, path):
        self.model[path][1] ^= True

    def get_irfs(self):
        return [row[0] for row in self.model if row[1]]

class AddNewStation(GetStringDialog):
    def __init__(self, parent):
        super(AddNewStation, self).__init__(
            parent, _("New Station"),
            _("Enter the location of an Internet radio station:"),
            okbutton=gtk.STOCK_ADD)
        b = qltk.Button(_("_Stations..."), gtk.STOCK_CONNECT)
        b.connect_object('clicked', self._val.set_text, SACREDCHAO)
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
        search = ValidatingEntry(Query.is_valid_color)
        lab.set_use_underline(True)
        lab.set_mnemonic_widget(search)
        clear = gtk.Button()
        clear.add(
            gtk.image_new_from_stock(gtk.STOCK_CLEAR, gtk.ICON_SIZE_MENU))
        search.connect('changed', self.__filter_changed)
        clear.connect_object('clicked', search.set_text, "")
        hb.pack_start(lab, expand=False)
        hb.pack_start(search)
        hb.pack_start(clear, expand=False)
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
                         queue=False, accels=songlist.accelerators)
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
        if uri.lower().endswith(".pls") or uri == SACREDCHAO:
            try: sock = urllib.urlopen(uri)
            except EnvironmentError, e:
                try: err = e.strerror.decode(const.ENCODING, 'replace')
                except TypeError:
                    err = e.strerror[1].decode(const.ENCODING, 'replace')
                qltk.ErrorMessage(None, _("Unable to add station"), err).run()
                return
            irfs = ParsePLS(sock)
        elif uri.lower().endswith(".m3u"):
            try: sock = urllib.urlopen(uri)
            except EnvironmentError, e:
                try: err = e.strerror.decode(const.ENCODING, 'replace')
                except TypeError:
                    err = e.strerror[1].decode(const.ENCODING, 'replace')
                qltk.ErrorMessage(None, _("Unable to add station"), err).run()
                return
            irfs = ParseM3U(sock)
        else:
            irfs = [IRFile(uri)]

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

import gst
if gst.element_make_from_uri(gst.URI_SRC, "http://", ""):
    browsers = [InternetRadio]
else: browsers = []
