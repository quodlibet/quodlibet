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
import player
import qltk.session
import stock
import util

from library import library
from plugins import PluginManager
from plugins.editing import EditingPlugins
from plugins.songsmenu import SongsMenuPlugins
from qltk.count import CountManager
from qltk.msg import ErrorMessage
from qltk.properties import SongProperties
from qltk.quodlibet import QuodLibetWindow
from qltk.remote import FSInterface, FIFOControl
from qltk.songlist import SongList
from qltk.songsmenu import SongsMenu
from qltk.trayicon import TrayIcon
from qltk.watcher import SongWatcher

global main, watcher
main = watcher = None

def website_wrap(activator, link):
    if not util.website(link):
        ErrorMessage(
            main, _("Unable to start web browser"),
            _("A web browser could not be found. Please set "
              "your $BROWSER variable, or make sure "
              "/usr/bin/sensible-browser exists.")).run()

def init():
    global main, watcher

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

    player.playlist.connect('error', player_error)

    watcher = SongWatcher()

    SongsMenu.plugins = SongsMenuPlugins(
        [os.path.join(const.BASEDIR, "plugins", "songsmenu"),
         os.path.join(const.USERDIR, "plugins", "songsmenu")], "songsmenu")
    SongsMenu.plugins.rescan()
    
    pm = PluginManager(watcher, player.playlist, [
        os.path.join(const.BASEDIR, "plugins"),
        os.path.join(const.USERDIR, "plugins")], "legacy")
    pm.rescan()

    SongProperties.plugins = EditingPlugins(
        [os.path.join(const.BASEDIR, "plugins", "editing"),
         os.path.join(const.USERDIR, "plugins", "editing")], "editing")

    in_all =("~filename ~uri ~#lastplayed ~#rating ~#playcount ~#skipcount "
             "~#added ~#bitrate ~current ~#laststarted ~basename "
             "~dirname").split()
    for Kind in zip(*browsers.browsers)[2]:
        if Kind.headers is not None: Kind.headers.extend(in_all)
        Kind.init(watcher)

    main = QuodLibetWindow(watcher, player.playlist)
    main.connect('destroy', gtk.main_quit)

    gtk.about_dialog_set_url_hook(website_wrap)

    # These stay alive in the watcher/other callbacks.
    FSInterface(player.playlist)
    FIFOControl(watcher, main, player.playlist)

    CountManager(watcher, player.playlist, main.playlist)

    TrayIcon(watcher, main, player.playlist)

    flag = main.songlist.get_columns()[-1].get_clickable
    while not flag(): gtk.main_iteration()
    song = library.get(config.get("memory", "song"))
    player.playlist.setup(main.playlist, song)
    main.show()

    return main

def save_library(window, player):
    window.destroy()
    player.destroy()

    # If something goes wrong here, it'll probably be caught
    # saving the library anyway.
    try: config.write(const.CONFIG)
    except EnvironmentError, err: pass

    for fn in [const.CONTROL, const.CURRENT]:
        # FIXME: CURRENT should be handled by FSInterface,
        # CONTROL by FIFOControl.
        try: os.unlink(fn)
        except EnvironmentError: pass

    try: library.save(const.LIBRARY)
    except EnvironmentError, err:
        err = str(err).decode('utf-8', 'replace')
        ErrorMessage(None, _("Unable to save library"), err).run()

def player_error(player, code, lock):
    if lock: gtk.threads_enter()
    ErrorMessage(
        main, _("Unable to play song"),
        _("GStreamer was unable to load the selected song.")
        + "\n\n" + code).run()
    if lock: gtk.threads_leave()

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
