# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os
import gobject, gtk, pango
import urllib

import const
import qltk

from browsers.base import Browser
from formats._audio import AudioFile
from library import Library
from widgets import widgets

STATIONS = os.path.join(const.DIR, "stations")

class IRFile(AudioFile):
    local = False
    __CAN_CHANGE = "title artist genre grouping version website".split()

    def __init__(self, uri):
        self["~uri"] = self["~filename"] = uri
        self["~mountpoint"] = ""
        self.sanitize(uri)

    def rename(self, newname): pass
    def reload(self): pass
    def exists(self): return True
    def valid(self): return True
    def mounted(self): return True
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
    while True:
        if "file%d" % count in data:
            irf = IRFile(data["file%d" % count])
            for key in ["title", "genre"]:
                try: irf[key] = data["%s%d" % (key, count)]
                except KeyError: pass
            try: irf["~#length"] = int(data["length%d" % count])
            except (KeyError, TypeError, ValueError): pass
            files.append(irf)
        else: break
        count += 1
    return files

class ChooseNewStations(gtk.Dialog):
    def __init__(self, irfs):
        gtk.Dialog.__init__(self, title=_("Choose New Stations"))
        self.add_buttons(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                         gtk.STOCK_ADD, gtk.RESPONSE_OK)
        self.set_default_size(400, 300)

        tv = qltk.HintedTreeView()
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
            model.append([song, False, song("title")])
        self.model = model
        self.connect_object('destroy', tv.set_model, None)
        self.child.show_all()

    def __toggled(self, toggle, path):
        self.model[path][1] ^= True

    def get_irfs(self):
        return [row[0] for row in self.model if row[1]]

class AddNewStation(qltk.GetStringDialog):
    def __init__(self):
        qltk.GetStringDialog.__init__(
            self, widgets.main, _("New Station"),
            _("Please enter the location of an Internet radio station."),
            okbutton = gtk.STOCK_ADD)

class InternetRadio(gtk.HBox, Browser):
    __gsignals__ = Browser.__gsignals__
    manageable = False
    __stations = Library()
    __sig = None

    def __init__(self, main=True):
        gtk.HBox.__init__(self)
        add = qltk.Button(_("_New Station"), gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        search = qltk.Button(_("_Search"), gtk.STOCK_FIND, gtk.ICON_SIZE_MENU)
        self.__search = entry = gtk.Entry()
        self.pack_start(add, expand=False)
        self.pack_start(entry)
        self.pack_start(search, expand=False)
        self.show_all()
        add.connect('clicked', self.__add)
        gobject.idle_add(self.activate)
        if InternetRadio.__sig is None:
            InternetRadio.__sig = widgets.watcher.connect(
                'changed', InternetRadio.__changed)

        for s in [widgets.watcher.connect('removed', self.activate),
                  widgets.watcher.connect('added', self.activate),
                  ]:
            self.connect_object('destroy', widgets.watcher.disconnect, s)
        self.__load_stations()

    def Menu(self, songs):
        m = gtk.Menu()
        rem = qltk.MenuItem(_("_Remove Station"), gtk.STOCK_REMOVE)
        m.append(rem)
        rem.connect('activate', self.__remove, songs)
        rem.show()
        return m

    def __remove(self, button, songs):
        map(self.__stations.remove, songs)
        widgets.watcher.removed(songs)
        self.__stations.save(STATIONS)
        self.activate()

    def __changed(self, watcher, songs):
        lib = self.__stations.values()
        if filter(lambda s: s in lib, songs):
            self.__stations.save(STATIONS)
    __changed = classmethod(__changed)

    def __add(self, button):
        uri = AddNewStation().run()
        if uri is None: return
        elif uri.lower().endswith(".pls"):
            sock = urllib.urlopen(uri)
            irfs = ParsePLS(sock)
            if not irfs:
                qltk.ErrorMessage(
                    None, _("No stations found"),
                    _("No internet radio stations were found at %s.") %
                    uri).run()
            elif len(irfs) == 1:
                if self.__stations.add_song(irfs[0]):
                    self.__stations.save(STATIONS)
                    widgets.watcher.added(irfs)
            else:
                d = ChooseNewStations(irfs)
                if d.run() == gtk.RESPONSE_OK:
                    irfs = d.get_irfs()
                    if irfs:
                        added = filter(self.__stations.add_song, irfs)
                        self.__stations.save(STATIONS)
                        widgets.watcher.added(irfs)
            d.destroy()
        else:
            if uri not in self.__stations:
                f = IRFile(uri)
                if self.__stations.add_song(f):
                    self.__stations.save(STATIONS)
                    widgets.watcher.added([f])

    def __load_stations(self):
        if not self.__stations: self.__stations.load(STATIONS)

    def restore(self): self.activate()
    def activate(self, *args):
        self.emit('songs-selected', self.__stations.values(), None)
        
    def save(self): pass

gobject.type_register(InternetRadio)

browsers = [(15, _("_Internet Radio"), InternetRadio, True)]
