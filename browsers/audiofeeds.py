# -*- coding: utf-8 -*-
# Copyright 2005 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os, sys

import gobject, gtk, pango
import const
import config
import parser
import qltk
import util

from widgets import widgets
from browsers.base import Browser
from formats.remote import RemoteFile

FEEDS = os.path.join(const.DIR, "feeds")

if sys.version_info < (2, 4): from sets import Set as set

class Feed(list):
    def __init__(self, uri):
        self.name = _("Unknown")
        self.uri = uri
        self.website = ""
        self.__lastgot = 0

    def parse(self):
        doc = feedparser.parse(self.uri)
        album = doc.channel.title
        website = doc.channel.link

        if album: self.name = album
        else: self.name = _("Unknown")
        if website: self.website = website

        entries = []
        uris = set()
        for entry in doc.entries:
            try: enclosures = entry.enclosures
            except (TypeError, AttributeError): pass
            else:
                for enclosure in enclosures:
                    if "audio" in enclosure.type:
                        entries.append((entry.title, enclosure.url))
                        uris.add(enclosure.url)
                        break

        for i, entry in list(self):
            if entry["~uri"] not in uris: self.remove(entry)
            else: uris.remove(entry["~uri"])

        entries.reverse()
        for title, uri in entries:
            if uri in uris:
                song = RemoteFile(uri)
                song["title"] = title
                song["album"] = self.name
                if self.website: song["website"] = self.website
                self.insert(0, song)
        return bool(uris)

class AddFeedDialog(qltk.GetStringDialog):
    def __init__(self):
        super(AddFeedDialog, self).__init__(
            widgets.main, _("New Feed"),
            _("Enter the location of an audio feed."),
            okbutton=gtk.STOCK_ADD)

    def run(self):
        uri = super(AddFeedDialog, self).run()
        if uri: return Feed(uri)
        else: return None

class AudioFeeds(Browser, gtk.VBox):
    __gsignals__ = Browser.__gsignals__

    __feeds = gtk.ListStore(bool, object) # unread, Feed

    headers = "title ~#rating ~#added ~#lastplayed".split()

    expand = qltk.RHPaned

    def cell_data(col, render, model, iter):
        if model[iter][0]:
            render.markup = "<b>%s</b>" % util.escape(model[iter][1].name)
        else: render.markup = util.escape(model[iter][1])
        render.set_property('markup', render.markup)
    cell_data = staticmethod(cell_data)

    def __init__(self, main):
        gtk.VBox.__init__(self)
        self.__main = main

        self.__view = view = qltk.HintedTreeView()
        self.__render = render = gtk.CellRendererText()
        render.set_property('ellipsize', pango.ELLIPSIZE_END)
        col = gtk.TreeViewColumn("Audio Feeds", render)
        col.set_cell_data_func(render, AudioFeeds.cell_data)
        view.append_column(col)
        view.set_model(self.__feeds)
        view.set_rules_hint(True)
        view.set_headers_visible(False)
        swin = gtk.ScrolledWindow()
        swin.set_shadow_type(gtk.SHADOW_IN)
        swin.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        swin.add(view)
        self.pack_start(swin)

        newpl = gtk.Button(stock=gtk.STOCK_NEW)
        newpl.connect('clicked', self.__new_feed)
        view.get_selection().connect('changed', self.__changed)

        self.pack_start(newpl, expand=False)
        self.show_all()

    def activate(self): self.__changed(self.__view.get_selection())

    def __changed(self, selection):
        model, iter = selection.get_selected()
        if iter:
            self.emit('songs-selected', list(model[iter][1]), True)

    def __new_feed(self, activator):
        feed = AddFeedDialog().run()
        if feed is not None:
            feed.parse()
            self.__feeds.append(row=[True, feed])

    def restore(self): pass

gobject.type_register(AudioFeeds)

try: import feedparser
except ImportError:
    try: import _feedparser as feedparser
    except ImportError: feedparser = None

if feedparser: browsers = [(20, _("_Audio Feeds"), AudioFeeds, True)]
else: browsers = []
