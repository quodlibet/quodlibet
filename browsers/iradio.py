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

TEST = ["http://64.236.34.196:80/stream/1018",
        "http://sc1.magnatune.com:8000/"
        ]
NAMES =  ["Groove Salad", "Magnatune Classical"]

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

    def restore(self):
        self.activate()

    def activate(self):
        self.emit('songs-selected', map(IRFile, TEST, NAMES), None)
        
    def save(self): pass

gobject.type_register(InternetRadio)

browsers = [(15, _("_Internet Radio"), InternetRadio, False)]
