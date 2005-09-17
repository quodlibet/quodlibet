# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject, gtk
import qltk

from browsers.base import Browser
from formats._audio import AudioFile

URIS = ["http://64.236.34.196:80/stream/1018",
        "http://sc1.magnatune.com:8000/"
        ]
NAMES =  ["Groove Salad", "Magnatune Classical"]

class AddNewStation(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self)
        self.set_title(_("New Station"))
        self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.add_button(gtk.STOCK_ADD, gtk.RESPONSE_OK)
        self.set_default_response(gtk.RESPONSE_OK)
        table = gtk.Table(2, 2)
        table.attach(gtk.Label(_("Name:")), 0, 1, 0, 1)
        self.__name = gtk.Entry()
        self.__name.set_activates_default(True)
        table.attach(self.__name, 1, 2, 0, 1)
        table.attach(gtk.Label(_("Location:")), 0, 1, 1, 2)
        self.__loc = gtk.Entry()
        self.__loc.set_activates_default(True)
        table.attach(self.__loc, 1, 2, 1, 2)
        table.show_all()
        table.set_border_width(12)
        table.set_col_spacings(6)
        table.set_row_spacings(12)
        self.vbox.pack_start(table)

    def run(self):
        resp = gtk.Dialog.run(self)
        if resp == gtk.RESPONSE_OK:
            ret = self.__name.get_text(), self.__loc.get_text()
        else: ret = None, None
        self.destroy()
        return ret

class IRFile(AudioFile):
    def __init__(self, uri, name):
        self["~uri"] = self["~filename"] = uri
        self["~mountpoint"] = ""
        self["title"] = name
        self.sanitize(uri)

    def rename(self, newname): pass
    def reload(self): pass
    def exists(self): return True
    def valid(self): return True
    def mounted(self): return True
    def can_change(self, k=None):
        if k is None: return []
        else: return False

class InternetRadio(gtk.HBox, Browser):
    __gsignals__ = Browser.__gsignals__
    def __init__(self, main=True):
        gtk.HBox.__init__(self)
        add = qltk.Button(_("New Station"), gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        search = qltk.Button(_("Search"), gtk.STOCK_FIND, gtk.ICON_SIZE_MENU)
        entry = gtk.Entry()
        self.pack_start(add, expand=False)
        self.pack_start(entry)
        self.pack_start(search, expand=False)
        self.show_all()
        add.connect('clicked', self.__add)
        gobject.idle_add(self.activate)

    def __add(self, buton):
        name, uri = AddNewStation().run()
        if name and uri:
            NAMES.append(name)
            URIS.append(uri)
            self.activate()

    def restore(self):
        self.activate()

    def activate(self):
        self.emit('songs-selected', map(IRFile, URIS, NAMES), None)
        
    def save(self): pass

gobject.type_register(InternetRadio)

browsers = [(15, _("_Internet Radio"), InternetRadio, False)]
