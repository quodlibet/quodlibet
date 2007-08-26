# -*- coding: utf-8 -*-
# Copyright 2004-2005 Joe Wreschnig, Michael Urman, Iñigo Serna
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation
#
# $Id$

import os

import gtk

from quodlibet import browsers
from quodlibet import config
from quodlibet import const
from quodlibet import stock
from quodlibet import util

from quodlibet.plugins.editing import EditingPlugins
from quodlibet.plugins.songsmenu import SongsMenuPlugins
from quodlibet.plugins.events import EventPlugins
from quodlibet.plugins.playorder import PlayOrderPlugins
from quodlibet.qltk import session
from quodlibet.qltk.tracker import SongTracker
from quodlibet.qltk.msg import ErrorMessage
from quodlibet.qltk.properties import SongProperties
from quodlibet.qltk.quodlibetwindow import QuodLibetWindow
from quodlibet.qltk.remote import FSInterface, FIFOControl
from quodlibet.qltk.songlist import SongList
from quodlibet.qltk.songsmenu import SongsMenu

try:
    from quodlibet.qltk.dbus_ import DBusHandler
except ImportError:
    DBusHandler = lambda player: None

global main, watcher
main = watcher = None

def website_wrap(activator, link):
    if not util.website(link):
        ErrorMessage(
            main, _("Unable to start web browser"),
            _("A web browser could not be found. Please set "
              "your $BROWSER variable, or make sure "
              "/usr/bin/sensible-browser exists.")).run()

def init(player, library):
    global main, watcher

    watcher = library.librarian

    session.init()

    icon = os.path.join(const.IMAGEDIR, "quodlibet.")
    try:
        pb = gtk.gdk.pixbuf_new_from_file_at_size(icon + "svg", 64, 64)
        gtk.window_set_default_icon(pb)
    except: gtk.window_set_default_icon_from_file(icon + "png")

    if config.get("settings", "headers").split() == []:
       config.set("settings", "headers", "title")
    headers = config.get("settings", "headers").split()
    SongList.set_all_column_headers(headers)
            
    for opt in config.options("header_maps"):
        val = config.get("header_maps", opt)
        util.HEADERS_FILTER[opt] = val

    in_all =("~filename ~uri ~#lastplayed ~#rating ~#playcount ~#skipcount "
             "~#added ~#bitrate ~current ~#laststarted ~basename "
             "~dirname").split()
    for Kind in browsers.browsers:
        if Kind.headers is not None: Kind.headers.extend(in_all)
        Kind.init(library)

    playorder = PlayOrderPlugins(
        [os.path.join(const.BASEDIR, "plugins", "playorder"),
         os.path.join(const.USERDIR, "plugins", "playorder")], "playorder")
    playorder.rescan()

    SongsMenu.plugins = SongsMenuPlugins(
        [os.path.join(const.BASEDIR, "plugins", "songsmenu"),
         os.path.join(const.USERDIR, "plugins", "songsmenu")], "songsmenu")
    SongsMenu.plugins.rescan()
    
    SongProperties.plugins = EditingPlugins(
        [os.path.join(const.BASEDIR, "plugins", "editing"),
         os.path.join(const.USERDIR, "plugins", "editing")], "editing")

    main = QuodLibetWindow(library, player)
    main.connect('destroy', gtk.main_quit)

    events = EventPlugins(library.librarian, player, [
        os.path.join(const.BASEDIR, "plugins", "events"),
        os.path.join(const.USERDIR, "plugins", "events")], "events")
    events.rescan()

    gtk.about_dialog_set_url_hook(website_wrap)

    # These stay alive in the library/player/other callbacks.
    FSInterface(player)
    FIFOControl(library, main, player)
    DBusHandler(player)
    SongTracker(library.librarian, player, main.playlist)

    flag = main.songlist.get_columns()[-1].get_clickable
    while not flag(): gtk.main_iteration()
    song = library.get(config.get("memory", "song"))
    player.setup(main.playlist, song)
    main.show()

    return main

def save_library(window, player, library):
    window.destroy()
    player.destroy()

    # If something goes wrong here, it'll probably be caught
    # saving the library anyway.
    try: config.write(const.CONFIG)
    except EnvironmentError, err: pass

    try: library.save(const.LIBRARY)
    except EnvironmentError, err:
        err = str(err).decode('utf-8', 'replace')
        ErrorMessage(None, _("Unable to save library"), err).run()
