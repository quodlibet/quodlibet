# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import gobject, gtk, pango
import config
import parser
import qltk

from browsers.base import Browser
from library import library

class BorgesBar(Browser, gtk.HBox):
    __gsignals__ = Browser.__gsignals__
    background = False

    def __init__(self, watcher, player):
        super(BorgesBar, self).__init__()
        model = gtk.ListStore(str, str)
        for row in [
            ("those that belong to The Emperor", "organization = emperor"),
            ("embalmed ones", "#(lastplayed > 1000 years)"),
            ("those that are trained", "#(rating != 2)"),
            ("suckling pigs", "artist = 'Raymond Watts'"),
            ("mermaids", "mermaid"),
            ("fabulous ones", "#(rating > 4)"),
            ("stray dogs", "album = /^$/"),
            ("those included in the present classification", "a s d f"),
            ("those that tremble as if they were mad", "#(bpm > 300)"),
            ("innumerable ones", "#(length > 1 year)"),
            ("those drawn with a very fine camelhair brush", "Who knows"),
            ("others", ";"),
            ("those that had just broken a flower vase", "#(mtime = now)"),
            ("those that from a long way off look like flies","#(length >= 0)")
            ]: model.append(row=row)
        combo = gtk.ComboBox(model)
        cell = gtk.CellRendererText()
        combo.pack_start(cell, True)
        combo.add_attribute(cell, 'text', 0)
        self.pack_start(combo)

        combo.connect('changed', self.__list_selected)

        self.connect_object('destroy', combo.set_model, None)
        self.show_all()

    def activate(self):
        self.__list_selected(*self.get_children())

    def restore(self): pass

    def __list_selected(self, combo):
        active = combo.get_active()
        if active == -1: return # Unset
        query = combo.get_model()[active][1]
        self.emit('songs-selected', library.query(query), None)

gobject.type_register(BorgesBar)

browsers = [
    (96, _("_Celestial Emporium of Benevolent Knowledge"), BorgesBar, True)]
