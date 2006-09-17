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

import browsers
import config
import const
import qltk.session
import stock
import util

from plugins.editing import EditingPlugins
from plugins.songsmenu import SongsMenuPlugins
from plugins.events import EventPlugins
from qltk.tracker import SongTracker
from qltk.msg import ErrorMessage
from qltk.properties import SongProperties
from qltk.quodlibet import QuodLibetWindow
from qltk.remote import FSInterface, FIFOControl
from qltk.songlist import SongList
from qltk.songsmenu import SongsMenu

try:
    from qltk.dbus_ import DBusHandler
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

    qltk.session.init()

    stock.init()

    icon = os.path.join(const.BASEDIR, "quodlibet.")
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

    player.connect('error', player_error)

    in_all =("~filename ~uri ~#lastplayed ~#rating ~#playcount ~#skipcount "
             "~#added ~#bitrate ~current ~#laststarted ~basename "
             "~dirname").split()
    for Kind in browsers.browsers:
        if Kind.headers is not None: Kind.headers.extend(in_all)
        Kind.init(library)

    main = QuodLibetWindow(library, player)
    main.connect('destroy', gtk.main_quit)

    SongsMenu.plugins = SongsMenuPlugins(
        [os.path.join(const.BASEDIR, "plugins", "songsmenu"),
         os.path.join(const.USERDIR, "plugins", "songsmenu")], "songsmenu")
    SongsMenu.plugins.rescan()
    
    events = EventPlugins(library.librarian, player, [
        os.path.join(const.BASEDIR, "plugins", "events"),
        os.path.join(const.USERDIR, "plugins", "events")], "events")
    events.rescan()

    SongProperties.plugins = EditingPlugins(
        [os.path.join(const.BASEDIR, "plugins", "editing"),
         os.path.join(const.USERDIR, "plugins", "editing")], "editing")

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

def player_error(player, code, lock):
    if lock: gtk.gdk.threads_enter()
    ErrorMessage(
        main, _("Unable to play song"),
        _("GStreamer was unable to load the selected song.")
        + "\n\n" + code).run()
    if lock: gtk.gdk.threads_leave()

def no_sink_quit(sink):
    header = _("Unable to open audio device")
    body = _("Quod Libet tried to access the 'autosink' and "
             "'%(sink)s' drivers but could not open them. Set your "
             "GStreamer pipeline by changing the\n"
             "    <b>pipeline = %(sink)s</b>\n"
             "line in ~/.quodlibet/config.") % {"sink": sink}
    ErrorMessage(None, header, body).run()
    gtk.main_quit()

def no_source_quit():
    header = _("Unable to open files")
    body = _("Quod Libet could not find the 'filesrc' GStreamer element. "
             "Check your GStreamer installation.")
    ErrorMessage(None, header, body).run()
    gtk.main_quit()
