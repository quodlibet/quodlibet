# -*- coding: utf-8 -*-
# Copyright 2006 Joe Wreschnig
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

# This is more a tech demo than something useful, I think.

import os

import gobject
import gtk
import pango

import config
import const
import qltk
import util

from browsers._base import Browser
from browsers.iradio import InternetRadio
from browsers.paned import PanedBrowser
from browsers.playlists import Playlists

# This is a Paned that is both horizontal and vertical. Don't ask.
class Rhythmbrox(Browser, qltk.RHPaned):
    __gsignals__ = Browser.__gsignals__

    name = _("Rhythmbrox")
    accelerated_name = _("_Rhythmbrox")
    priority = 10

    __proxy_id = None

    def expand(self):
        return self

    def pack1(self, *args, **kwargs):
        # This is called once, use it to really set up. QLW thinks it's
        # packing a browser, but we're the browser.
        view = gtk.TreeView()
        col = gtk.TreeViewColumn(_("Sources"), gtk.CellRendererText(), text=0)
        view.append_column(col)
        frame = gtk.ScrolledWindow()
        frame.set_shadow_type(gtk.SHADOW_IN)
        frame.add(view)
        frame.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        qltk.RHPaned.pack1(self, frame)

        self.__paned = PanedBrowser(self.__library, self.__player)
        self.__iradio = InternetRadio(self.__library, self.__player)
        model = gtk.TreeStore(str, object)
        model.append(None, [_("Library"), self.__paned])
        model.append(None, [_("Radio Stations"), self.__iradio])
        iter = model.append(None, [_("Playlists"), None])
        for playlist in Playlists.playlists():
            model.append(iter, [playlist.name, playlist])

        view.set_model(model)
        view.get_selection().connect('changed', self.__set_browser)
        self.show_all()

    def pack_browser(self, browser):
        if self.get_child2():
            if self.browser is None:
                self.remove(self.get_child2())
            else:
                self.get_child2().remove(self.browser)
                self.get_child2().remove(self.__songlist)
                self.get_child2().destroy()
                self.browser.disconnect(self.__proxy_id)

        if browser is None:
            qltk.RHPaned.pack2(self, self.__songlist, resize=True)
            self.browser = None
            return

        browser.show()
        if browser.expand:
            container = browser.expand()
            container.pack1(browser, resize=True)
            container.pack2(self.__songlist, resize=True)
            try:
                key = "%s_pos" % self.browser.__class__.__name__
                val = config.getfloat("browsers", key)
            except: val = 0.4
            def set_size(paned, alloc, pos):
                paned.set_relative(pos)
                paned.disconnect(paned._size_sig)
                del(paned._size_sig)
            sig = container.connect('size-allocate', set_size, val)
            container._size_sig = sig
        else:
            container = gtk.VBox(spacing=6)
            container.pack_start(browser, expand=False)
            container.pack_start(self.__songlist)
        container.show()
        qltk.RHPaned.pack2(self, container, resize=True)
        self.browser = browser
        self.__proxy_id = self.browser.connect_object(
            'songs-selected', self.emit, 'songs-selected')
        self.browser.activate()

    def pack2(self, songlist, **kwargs):
        self.__songlist = songlist
        if not self.get_child2():
            self.pack_browser(self.__paned)

    def __init__(self, library, player):
        super(Rhythmbrox, self).__init__()
        self.__library = library
        self.__player = player

    def __set_browser(self, selection):
        model, iter = selection.get_selected()
        browser = model[iter][1]
        if isinstance(browser, list):
            self.pack_browser(None)
            self.emit('songs-selected', list(browser), True)
        else:
            self.pack_browser(browser)

browsers = [Rhythmbrox]
