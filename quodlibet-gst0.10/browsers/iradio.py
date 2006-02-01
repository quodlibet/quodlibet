# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

SACREDCHAO = ("http://www.sacredchao.net/quodlibet/wiki/QL/"
              "Master.qlpls?format=txt")

import os
import gobject, gtk, pango
import urllib

import const
import qltk
import util

from browsers._base import Browser
from formats.remote import RemoteFile
from library import Library
from qltk.getstring import GetStringDialog
from qltk.entry import ValidatingEntry
from parse import Query

STATIONS = os.path.join(const.DIR, "stations")

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

class ChooseNewStations(gtk.Dialog):
    def __init__(self, irfs):
        gtk.Dialog.__init__(self, title=_("Choose New Stations"))
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
    __stations = Library()
    __sig = None
    __filter = None
    __refill_id = None

    headers = "title artist grouping genre website".split()

    def __init__(self, watcher, player):
        gtk.HBox.__init__(self, spacing=12)
        add = qltk.Button(_("_New Station"), gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        self.__search = gtk.Entry()
        self.pack_start(add, expand=False)
        add.connect('clicked', self.__add, watcher)
        if InternetRadio.__sig is None:
            InternetRadio.__sig = watcher.connect(
                'changed', InternetRadio.__changed)

        for s in [watcher.connect('removed', self.activate),
                  watcher.connect('added', self.activate),
                  ]:
            self.connect_object('destroy', watcher.disconnect, s)
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

        self.__load_stations()
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

    def Menu(self, songs, songlist):
        m = gtk.Menu()
        rem = qltk.MenuItem(_("_Remove Station"), gtk.STOCK_REMOVE)
        m.append(rem)
        rem.connect('activate', self.__remove, songs)
        rem.show()
        return m

    def __remove(self, button, songs):
        map(self.__stations.remove, songs)
        from widgets import watcher
        watcher.removed(songs)
        self.__stations.save(STATIONS)
        self.activate()

    def __changed(klass, watcher, songs):
        lib = klass.__stations.values()
        if filter(lambda s: s in lib, songs):
            klass.__stations.save(STATIONS)
    __changed = classmethod(__changed)

    def __add(self, button, watcher):
        uri = (AddNewStation(qltk.get_top_parent(self)).run() or "").strip()
        if uri == "": return
        elif uri.lower().endswith(".pls") or uri == SACREDCHAO:
            if isinstance(uri, unicode): uri = uri.encode('utf-8')
            try: sock = urllib.urlopen(uri)
            except EnvironmentError, e:
                try: err = unicode(e.strerror, errors='replace')
                except TypeError:
                    err = unicode(e.strerror[1], errors='replace')
                qltk.ErrorMessage(None, _("Unable to add station"), err).run()
                return
            irfs = ParsePLS(sock)
            if not irfs:
                qltk.ErrorMessage(
                    None, _("No stations found"),
                    _("No Internet radio stations were found at %s.") %
                    uri).run()
                return

            irfs = filter(
                lambda s: not self.__stations.has_key(s["~uri"]), irfs)
            if not irfs:
                qltk.ErrorMessage(
                    None, _("No new stations"),
                    _("All stations listed are already in your library.")
                    ).run()
            elif len(irfs) == 1:
                if self.__stations.add_song(irfs[0]):
                    self.__stations.save(STATIONS)
                    watcher.added(irfs)
            else:
                irfs.sort()
                d = ChooseNewStations(irfs)
                if d.run() == gtk.RESPONSE_OK:
                    irfs = d.get_irfs()
                    if irfs:
                        added = filter(self.__stations.add_song, irfs)
                        self.__stations.save(STATIONS)
                        watcher.added(added)
                d.destroy()
        elif uri.lower().endswith(".m3u"):
            qltk.WarningMessage(
                None, _("Unsupported file type"),
                _("M3U playlists cannot be loaded.")).run()
        else:
            if uri not in self.__stations:
                f = IRFile(uri)
                if self.__stations.add_song(f):
                    self.__stations.save(STATIONS)
                    watcher.added([f])
                else:
                    qltk.WarningMessage(
                        None, _("No new stations"),
                        _("This station is already in your library.") %
                        uri).run()

    def __load_stations(self):
        if not self.__stations: self.__stations.load(STATIONS)

    def restore(self): self.activate()
    def activate(self, *args):
        self.emit('songs-selected',
                  filter(self.__filter, self.__stations.values()), None)
        
    def save(self): pass

    def statusbar(self, i):
        return ngettext("%(count)d station", "%(count)d stations", i)

gobject.type_register(InternetRadio)

import gst
if gst.element_make_from_uri(gst.URI_SRC, "http://", ""):
    browsers = [(15, _("_Internet Radio"), InternetRadio, True)]
else: browsers = []
