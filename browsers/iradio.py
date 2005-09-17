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

class IRFile(AudioFile):
    local = False

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
        if k is None: return []
        else: return False

def ParsePLS(file):
    data = {}
    lines = file.readlines()
    if not lines or "[playlist]" not in lines.pop(0): return []

    for line in lines:
        try: head, val = line.strip().split("=", 1)
        except TypeError: continue
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
            try: irf["~#rating"] = int(data["rating%d" % count])
            except (KeyError, TypeError, ValueError): pass
            try: irf["~#length"] = int(data["length%d" % count])
            except (KeyError, TypeError, ValueError): pass
        else: break
    return files

FILES = map(IRFile, ["http://64.236.34.196:80/stream/1018",
                     "http://sc1.magnatune.com:8000/",
                     "http://64.236.34.4:80/stream/1065",
                     ]
            )

class AddNewStation(qltk.GetStringDialog):
    def __init__(self):
        qltk.GetStringDialog.__init__(
            self, None, _("New Station"),
            _("Please enter the location of an Internet radio station."),
            okbutton = gtk.STOCK_ADD)

class InternetRadio(gtk.HBox, Browser):
    __gsignals__ = Browser.__gsignals__
    manageable = False

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

    def __add(self, button):
        name, uri = AddNewStation().run()
        if uri.lower().endswith(".pls"):
            print "PLS files unsupported yet!"
        else:
            FILES.append(uri)
            self.activate()

    def restore(self):
        self.activate()

    def activate(self):
        self.emit('songs-selected', FILES, None)
        
    def save(self): pass

gobject.type_register(InternetRadio)

browsers = [(15, _("_Internet Radio"), InternetRadio, False)]
